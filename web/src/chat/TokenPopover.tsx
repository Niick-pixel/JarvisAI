// The top alternatives at one token. Picking one truncates the message there, forces your choice,
// and generation carries on — steering at the token level.
import { motion } from "framer-motion";
import type { TokenView } from "../api/types";
import { BOUNCE } from "../ui/motion";

export default function TokenPopover({
  token,
  onPick,
  onClose,
}: {
  token: TokenView;
  onPick: (alternative: string) => void;
  onClose: () => void;
}) {
  if (token.top.length === 0) {
    return (
      <motion.span
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={BOUNCE}
        className="absolute left-0 top-full z-40 mt-1 w-64 rounded-2xl border border-ink/[0.06] bg-raised p-3 text-[12px] text-ink-faint shadow-float"
      >
        This backend reported no alternatives for this token.
        <button onClick={onClose} className="ml-2 underline">
          close
        </button>
      </motion.span>
    );
  }

  return (
    <motion.span
      initial={{ opacity: 0, y: 4, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={BOUNCE}
      className="absolute left-0 top-full z-40 mt-1 block w-72 rounded-2xl border border-ink/[0.06] bg-raised p-1.5 shadow-float"
    >
      <span className="mb-1 flex items-center justify-between px-2 py-1 text-[12px] text-ink-faint">
        <span>Other words it considered</span>
        <button onClick={onClose} className="hover:text-ink">
          ✕
        </button>
      </span>
      {token.top.map((alternative, index) => {
        const p = Math.exp(alternative.logprob);
        const chosen = index === 0;
        return (
          <button
            key={`${alternative.token}-${index}`}
            onClick={() => onPick(alternative.token)}
            className="flex w-full items-center gap-2 rounded-xl px-2 py-1.5 text-left hover:bg-ink/[0.05]"
            title={chosen ? "What the model actually picked" : "Force this instead and continue"}
          >
            <span className="min-w-0 flex-1 truncate font-mono text-[12px] text-ink">
              {alternative.token === "" ? "∅" : alternative.token}
            </span>
            <span className="h-1 w-16 overflow-hidden rounded-full bg-ink/10">
              <span
                className="block h-full rounded-full bg-accent"
                style={{ width: `${Math.max(2, p * 100)}%` }}
              />
            </span>
            <span className="w-10 text-right font-mono text-[10px] text-ink-faint">
              {p.toFixed(2)}
            </span>
          </button>
        );
      })}
    </motion.span>
  );
}
