// A picture on its way: what was asked for, and how far stable-diffusion.cpp has got.
import { motion } from "framer-motion";
import Orb from "../brand/Orb";
import { useImages } from "../store/images";
import { BOUNCE } from "../ui/motion";

export default function Painting() {
  const prompt = useImages((s) => s.painting);
  const status = useImages((s) => s.status);
  if (!prompt) return null;
  const share = status?.total ? status.step / status.total : 0;
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={BOUNCE} className="flex gap-4">
      <div className="pt-0.5">
        <Orb size={26} state="thinking" />
      </div>
      <div className="w-[320px] max-w-full">
        <div className="flex aspect-square animate-pulse items-end rounded-3xl bg-ink/[0.07] p-4">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink/[0.08]">
            <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${Math.max(4, share * 100)}%` }} />
          </div>
        </div>
        <p className="mt-2 text-[13px] text-ink-muted">
          {status?.total ? `Painting - step ${status.step} of ${status.total}` : "Loading the image model…"}
        </p>
      </div>
    </motion.div>
  );
}
