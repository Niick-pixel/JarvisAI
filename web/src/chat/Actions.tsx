// The row under an answer: copy, try again, read it aloud, and "more" for the tools no hosted
// assistant has - carry on from here, edit its words, replay it exactly, see how sure it was.
import { Check, Copy, Ellipsis, GitCompare, Pencil, Play, RefreshCw, Repeat, ScanEye, Square, Volume2 } from "lucide-react";
import { useState } from "react";
import type { Message } from "../api/types";
import { useGraph } from "../store/graph";
import { useSession } from "../store/session";
import { toast } from "../store/toast";
import { useVoice } from "../store/voice";
import { useXray } from "../store/xray";
import { IconButton } from "../ui/controls";
import Menu, { type MenuItem } from "../ui/Menu";
import SiblingNav from "./SiblingNav";
import { split } from "./thinking";

export function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <IconButton
      icon={done ? Check : Copy}
      label={done ? "Copied" : "Copy"}
      size={32}
      onClick={() =>
        void navigator.clipboard?.writeText(text).then(() => {
          setDone(true);
          window.setTimeout(() => setDone(false), 1400);
        })
      }
    />
  );
}

export default function Actions({
  message,
  showDiff,
  onToggleDiff,
}: {
  message: Message;
  showDiff: boolean;
  onToggleDiff: () => void;
}) {
  const answer = split(message.content).answer;
  const regenerate = useSession((s) => s.regenerate);
  const continueFrom = useSession((s) => s.continueFrom);
  const rerun = useSession((s) => s.rerun);
  const beginEdit = useGraph((s) => s.beginEdit);
  const xrayOn = useXray((s) => s.enabled[message.id]) ?? false;
  const toggleXray = useXray((s) => s.toggle);
  const speak = useVoice((s) => s.speak);
  const hush = useVoice((s) => s.hush);
  const tts = useVoice((s) => s.status?.tts);
  const speaking = useVoice((s) => s.speakingId === message.id);

  const onSpeak = () => {
    if (speaking) return hush();
    if (tts && !tts.available) return toast(`${tts.reason} ${tts.fix ?? ""}`.trim(), "error");
    void speak(message.id, answer);
  };

  const more: MenuItem[] = [
    {
      key: "continue",
      label: "Continue writing",
      detail: "Pick up exactly where it stopped",
      icon: Play,
      onSelect: () => void continueFrom(message.id),
    },
    {
      key: "edit",
      label: "Edit answer",
      detail: "Change its words; the original is kept",
      icon: Pencil,
      onSelect: () => beginEdit(message.id),
    },
    {
      key: "replay",
      label: "Replay exactly",
      detail: "Same seed and settings, to check it repeats",
      icon: Repeat,
      onSelect: () => void rerun(message.id),
    },
    {
      key: "xray",
      label: xrayOn ? "Hide confidence" : "Show confidence",
      detail: "Tint each word by how sure the model was",
      icon: ScanEye,
      checked: xrayOn,
      onSelect: () => void toggleXray(message.id),
    },
  ];
  if (message.forked_reason === "rerun") {
    more.push({
      key: "diff",
      label: showDiff ? "Hide differences" : "Compare with original",
      icon: GitCompare,
      checked: showDiff,
      onSelect: onToggleDiff,
    });
  }

  return (
    <div className="-ml-1.5 mt-2 flex items-center gap-0.5 text-ink-faint">
      <SiblingNav messageId={message.id} />
      <CopyButton text={answer} />
      <IconButton icon={RefreshCw} label="Try again" size={32} onClick={() => void regenerate(message.id)} />
      <IconButton icon={speaking ? Square : Volume2} label={speaking ? "Stop reading" : "Read aloud"} size={32} active={speaking} onClick={onSpeak} />
      <Menu
        place="top-start"
        width={290}
        items={more}
        trigger={(open, toggle) => <IconButton icon={Ellipsis} label="More" size={32} active={open} onClick={toggle} />}
      />
    </div>
  );
}
