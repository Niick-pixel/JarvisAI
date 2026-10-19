"""Files: edits found and applied (or honestly refused), chosen hunk by hunk, never outside the
folder, never over a newer file, always undoable - and Word documents keep their formatting."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import MODEL_ID, FakeProvider

from server.files import edits
from server.files.propose import Proposals
from server.files.workspace import Workspace
from server.models.files import ProposeRequest
from server.providers.registry import ProviderRegistry
from server.tools.sandbox import Denied

CODE = "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n"


def block(search: str, replace: str) -> str:
    return f"<<<<<<< SEARCH\n{search}\n=======\n{replace}\n>>>>>>> REPLACE\n"


def test_blocks_apply_exactly_loosely_or_are_reported() -> None:
    reply = (
        block("    return a + b", "    return int(a) + int(b)")
        + block(
            "def sub(a, b):\n  return a - b", "def sub(a, b):\n    return a - b - 0"
        )  # indent off
        + block("def mul(a, b):", "def mul(a, b, c):")  # not in the file
        + "Summary: made add take ints\n"
    )
    found, summary = edits.parse(reply, CODE)
    new, failed = edits.apply_blocks(CODE, found)
    assert summary == "made add take ints"
    assert "int(a) + int(b)" in new and "a - b - 0" in new
    assert failed == ["def mul(a, b):"]


def test_a_whole_file_answer_still_works() -> None:
    reply = "```python\n" + CODE.replace("a + b", "b + a") + "```"
    found, _ = edits.parse(reply, CODE)
    assert edits.apply_blocks(CODE, found)[0] == CODE.replace("a + b", "b + a")


def test_only_the_hunks_you_keep_are_applied() -> None:
    new = CODE.replace("a + b", "A").replace("a - b", "S")
    assert len(edits.hunks(CODE, new)) == 2
    assert edits.apply_hunks(CODE, new, {1}) == CODE.replace("a - b", "S")
    assert edits.apply_hunks(CODE, new, None) == new


@pytest.fixture
def space(tmp_path: Path) -> tuple[Workspace, str, Path]:
    folder = tmp_path / "project"
    folder.mkdir()
    (folder / "calc.py").write_text(CODE)
    (folder / ".env").write_text("SECRET=1")
    (folder / "node_modules").mkdir()
    workspace = Workspace(tmp_path / "data")
    return workspace, workspace.add_root(str(folder)).id, folder


def test_the_folder_is_the_fence(space: tuple[Workspace, str, Path]) -> None:
    workspace, root, _ = space
    assert [e.name for e in workspace.listing(root)] == ["calc.py"]  # no .env, no node_modules
    for bad in ("../outside.txt", ".env"):
        with pytest.raises(Denied):
            workspace.read(root, bad)


def test_saves_refuse_a_stale_version_and_undo_restores(space: tuple[Workspace, str, Path]) -> None:
    workspace, root, folder = space
    opened = workspace.read(root, "calc.py")
    (folder / "calc.py").write_text(CODE + "# edited elsewhere\n")
    with pytest.raises(Denied, match="changed on disk"):
        workspace.write(root, "calc.py", opened.version, "x")
    fresh = workspace.read(root, "calc.py")
    saved = workspace.write(root, "calc.py", fresh.version, "print('hi')\n")
    assert saved.text == "print('hi')\n" and saved.can_undo
    assert workspace.undo(root, "calc.py").text == CODE + "# edited elsewhere\n"


async def test_a_proposal_is_reviewed_then_applied(space: tuple[Workspace, str, Path]) -> None:
    workspace, root, folder = space
    reply = block("    return a + b", "    return a + b  # sum") + block(
        "    return a - b", "    return a - b  # difference"
    )
    proposals = Proposals(
        workspace, ProviderRegistry([FakeProvider(script=[reply, "Summary: notes"])])
    )
    request = ProposeRequest(root=root, path="calc.py", instruction="comment the returns")
    proposal = await proposals.propose(request, MODEL_ID)
    assert (folder / "calc.py").read_text() == CODE  # nothing written yet
    assert len(proposal.hunks) == 2 and proposal.summary == "notes" and not proposal.failed
    result = proposals.apply(proposal.id, [0])
    assert "# sum" in result.text and "# difference" not in result.text


def test_word_documents_keep_their_formatting(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    folder = tmp_path / "docs"
    folder.mkdir()
    document = docx.Document()
    document.add_heading("Plan", level=1)
    intro = document.add_paragraph()
    intro.add_run("Bold start").bold = True
    intro.add_run(" and the rest.")
    document.add_paragraph("Delete me.")
    document.add_table(rows=1, cols=2).cell(0, 0).text = "kept"
    document.save(str(folder / "plan.docx"))

    workspace = Workspace(tmp_path / "data")
    root = workspace.add_root(str(folder)).id
    opened = workspace.read(root, "plan.docx")
    assert opened.kind == "docx" and opened.text.split("\n")[:3] == [
        "# Plan",
        "Bold start and the rest.",
        "Delete me.",
    ]
    edited = opened.text.replace(
        "Bold start and the rest.", "Bold start, rewritten.\n## Next steps"
    )
    edited = edited.replace("\nDelete me.", "")
    workspace.write(root, "plan.docx", opened.version, edited)

    saved = docx.Document(str(folder / "plan.docx"))
    texts = [p.text for p in saved.paragraphs]
    assert (
        texts[:3] == ["Plan", "Bold start, rewritten.", "Next steps"] and "Delete me." not in texts
    )
    assert saved.paragraphs[1].runs[0].bold is True  # the first run's formatting survived
    assert saved.paragraphs[2].style.name == "Heading 2"
    assert saved.tables[0].cell(0, 0).text == "kept"  # what Files cannot see is untouched
