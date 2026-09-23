// Editing any message, including the assistant's own. Saving forks a sibling; the original stays
// exactly where it was. This is the one thing no hosted chat product will let you do.
import { useEffect, useRef, useState } from "react";
import { useGraph } from "../store/graph";
import { useSession } from "../store/session";
import { Button, FIELD } from "../ui/controls";

export default function EditMessage({
  messageId,
  initial,
  isAssistant,
}: {
  messageId: string;
  initial: string;
  isAssistant: boolean;
}) {
  const [draft, setDraft] = useState(initial);
  const { saveEdit, cancelEdit } = useGraph();
  const continueFrom = useSession((s) => s.continueFrom);
  const area = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    area.current?.focus();
    area.current?.setSelectionRange(draft.length, draft.length);
    // Focus once on open; re-focusing on every keystroke would fight the caret.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const save = async () => {
    await saveEdit(messageId, draft);
  };

  const saveAndContinue = async () => {
    const forkedId = await saveEdit(messageId, draft);
    if (forkedId) await continueFrom(forkedId);
  };

  return (
    <div className="flex flex-col gap-2">
      <textarea
        ref={area}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Escape") cancelEdit();
          if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) void save();
        }}
        rows={Math.min(16, draft.split("\n").length + 2)}
        className={`${FIELD} resize-y leading-relaxed`}
      />
      <div className="flex flex-wrap items-center gap-2 text-[12px] text-ink-faint">
        <Button tone="primary" small onClick={() => void save()}>
          Save
        </Button>
        {isAssistant && (
          <Button
            small
            onClick={() => void saveAndContinue()}
            title="Fork with your text, then let the model carry on from it"
          >
            Save and continue
          </Button>
        )}
        <Button small tone="ghost" onClick={cancelEdit}>
          Cancel
        </Button>
        <span className="ml-auto">The original is kept - Ctrl+Enter saves</span>
      </div>
    </div>
  );
}
