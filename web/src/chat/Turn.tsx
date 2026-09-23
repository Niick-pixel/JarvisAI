// One turn of the conversation. Yours sits on the right in a soft bubble; Jarvis answers on the
// open page, with its thinking folded away above and a quiet row of actions below.
import { motion } from "framer-motion";
import { Pencil } from "lucide-react";
import { useState } from "react";
import type { Message } from "../api/types";
import Orb from "../brand/Orb";
import { useGraph } from "../store/graph";
import { useSession } from "../store/session";
import { useXray } from "../store/xray";
import { IconButton } from "../ui/controls";
import { BOUNCE } from "../ui/motion";
import Actions, { CopyButton } from "./Actions";
import EditMessage from "./EditMessage";
import Markdown from "./Markdown";
import ReplayDiff from "./ReplayDiff";
import SiblingNav from "./SiblingNav";
import Thinking from "./Thinking";
import { split } from "./thinking";
import XRay from "./XRay";

const arrive = { initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0 }, transition: BOUNCE };

export function UserTurn({ message }: { message: Message }) {
  const editing = useGraph((s) => s.editing) === message.id;
  const beginEdit = useGraph((s) => s.beginEdit);
  if (editing) {
    return (
      <div className="ml-auto w-full max-w-[85%]">
        <EditMessage messageId={message.id} initial={message.content} isAssistant={false} />
      </div>
    );
  }
  return (
    <motion.div {...arrive} className="group flex flex-col items-end">
      <div className="max-w-[85%] whitespace-pre-wrap rounded-[22px] rounded-br-lg bg-bubble px-5 py-3 text-[15.5px] leading-relaxed text-ink">
        {message.content}
      </div>
      <div className="mt-1 flex items-center gap-0.5 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
        <SiblingNav messageId={message.id} />
        <CopyButton text={message.content} />
        <IconButton icon={Pencil} label="Edit" size={32} onClick={() => beginEdit(message.id)} />
      </div>
    </motion.div>
  );
}

export function AssistantTurn({ message, streaming }: { message: Message; streaming: boolean }) {
  const liveText = useSession((s) => (streaming ? s.streamingText : ""));
  const thoughtMs = useSession((s) => s.thoughtMs[message.id]);
  const running = useSession((s) => s.runId) !== null;
  const editing = useGraph((s) => s.editing) === message.id;
  const xrayOn = useXray((s) => s.enabled[message.id]) ?? false;
  const xray = useXray((s) => s.data[message.id]);
  const force = useXray((s) => s.force);
  const messages = useSession((s) => s.messages);
  const [showDiff, setShowDiff] = useState(false);

  const raw = streaming ? liveText : message.content;
  const { thinking, answer, open } = split(raw);
  const waiting = streaming && raw === "";

  return (
    <motion.div {...arrive} className="flex gap-4">
      <div className="pt-0.5">
        <Orb size={26} state={streaming ? "thinking" : "idle"} />
      </div>
      <div className="min-w-0 flex-1">
        {waiting && <p className="shimmer pt-0.5 text-[15px] font-medium">Thinking</p>}
        {(thinking || open) && <Thinking text={thinking} live={streaming && open} ms={thoughtMs} />}

        {editing ? (
          <EditMessage messageId={message.id} initial={message.content} isAssistant />
        ) : xrayOn && xray?.supports_logprobs && !streaming ? (
          <div className="text-[15.5px]">
            <XRay data={xray} content={message.content} onForce={(i, t) => void force(message.id, i, t)} />
          </div>
        ) : (
          answer && <Markdown text={answer} />
        )}

        {xrayOn && xray && !xray.supports_logprobs && (
          <p className="mt-2 text-[13px] text-ink-faint">
            This model didn't report how sure it was about each word, so there is nothing to show.
          </p>
        )}
        {message.status === "stopped" && !streaming && (
          <p className="mt-2 text-[13px] text-ink-faint">Stopped - what it wrote so far is kept.</p>
        )}
        {message.status === "error" && !streaming && (
          <p className="mt-2 text-[13px] text-danger">This answer didn't finish.</p>
        )}
        {showDiff && (
          <div className="mt-3">
            <ReplayDiff message={message} original={messages.find((m) => m.id === message.edited_from_id)} />
          </div>
        )}
        {!streaming && !running && !editing && (
          <Actions message={message} showDiff={showDiff} onToggleDiff={() => setShowDiff(!showDiff)} />
        )}
      </div>
    </motion.div>
  );
}
