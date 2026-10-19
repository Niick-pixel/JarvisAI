"""Asking the model for a change to one file, and holding its answer until you decide.

A proposal is computed against the file as it was read; applying it re-reads the file and refuses
if anything changed in between, so an edit can never land on text it was not written for.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass

from server.chat import thinking
from server.files import edits
from server.files.workspace import Workspace
from server.ids import new_id
from server.models.files import FileContent, Proposal, ProposeRequest
from server.models.params import SamplingParams
from server.providers.base import PromptMessage, Token
from server.providers.registry import ProviderRegistry
from server.tools.sandbox import Denied

KEPT = 20
CHARS_PER_TOKEN = 3.5
SYSTEM = """You edit one file at a time. Answer with edit blocks only, in exactly this form:

<<<<<<< SEARCH
lines copied exactly from the file
=======
the lines that replace them
>>>>>>> REPLACE

Rules:
- Copy SEARCH text character for character from the file, indentation included.
- Keep each SEARCH short: just enough lines to be unique.
- To add text, SEARCH for the line next to where it goes and repeat it in REPLACE with the new text.
- To delete, leave REPLACE empty.
- Use as many blocks as the change needs. Change nothing that was not asked for.
After the blocks, write one line: "Summary: " and what you changed."""
DOCX_HINT = (
    "\nThis is a Word document shown as one line per paragraph. Lines starting with # are "
    "headings. Keep one paragraph per line."
)


class TooLarge(ValueError):
    pass


@dataclass
class Pending:
    proposal: Proposal
    original: str
    proposed: str


class Proposals:
    def __init__(self, workspace: Workspace, registry: ProviderRegistry) -> None:
        self.workspace = workspace
        self.registry = registry
        self._pending: OrderedDict[str, Pending] = OrderedDict()

    async def propose(self, request: ProposeRequest, model_id: str) -> Proposal:
        current = self.workspace.read(request.root, request.path)
        provider, model = await self.registry.resolve(model_id)
        ctx = min(model.ctx_len_max or 8192, 32768)
        prompt = self._prompt(current, request.instruction)
        needed = int(len(SYSTEM + prompt) / CHARS_PER_TOKEN)
        room = ctx - needed - 256
        if room < 512:
            raise TooLarge(
                f"{request.path} is about {needed:,} tokens and this model's context is {ctx:,}. "
                "Ask about a smaller file, or load a model with a longer context."
            )
        params = SamplingParams(
            seed=0,
            temperature=0.2,
            max_tokens=min(room, 8192),
            n_probs=0,
            thinking=request.thinking,
        )
        started = time.perf_counter()
        reply = ""
        async for item in provider.stream(
            [
                PromptMessage(role="system", content=SYSTEM),
                PromptMessage(role="user", content=prompt),
            ],
            params,
            model_id=model.id,
            ctx_len=ctx,
        ):
            if isinstance(item, Token):
                reply += item.text
        answer = thinking.split(reply)[1] if "<think>" in reply else reply
        blocks, summary = edits.parse(answer, current.text)
        if not blocks:
            raise Denied(
                "The model did not answer with any edits. Try saying exactly what to change."
            )
        proposed, failed = edits.apply_blocks(current.text, blocks)
        proposal = Proposal(
            id=new_id("prop"),
            root=request.root,
            path=request.path,
            version=current.version,
            summary=summary or "Proposed changes",
            hunks=edits.hunks(current.text, proposed),
            failed=failed,
            model_id=model.id,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        self._pending[proposal.id] = Pending(proposal, current.text, proposed)
        while len(self._pending) > KEPT:
            self._pending.popitem(last=False)
        return proposal

    def _prompt(self, current: FileContent, instruction: str) -> str:
        hint = DOCX_HINT if current.kind == "docx" else ""
        return (
            f"File: {current.path}{hint}\n```\n{current.text}\n```\n\nChange: {instruction.strip()}"
        )

    def apply(self, proposal_id: str, keep: list[int] | None) -> FileContent:
        pending = self._pending.get(proposal_id)
        if pending is None:
            raise Denied("That proposal has expired. Ask again.")
        p = pending.proposal
        merged = edits.apply_hunks(
            pending.original, pending.proposed, None if keep is None else set(keep)
        )
        result = self.workspace.write(p.root, p.path, p.version, merged)
        del self._pending[proposal_id]
        return result

    def discard(self, proposal_id: str) -> None:
        self._pending.pop(proposal_id, None)
