// What forecasting needs before the first run: PyTorch in the app (always, in the installed
// app), and the Kronos weights, fetched here with a progress bar - only when this is pressed.
import { motion } from "framer-motion";
import { Download } from "lucide-react";
import { useForecast } from "../store/forecast";
import { Button } from "../ui/controls";
import { GLIDE } from "../ui/motion";

function mb(bytes: number): string {
  return `${Math.round(bytes / 1e6).toLocaleString()} MB`;
}

export default function Setup() {
  const { status, pack, getModel } = useForecast();
  if (!status || (status.runtime && status.weights)) return null;

  if (!status.runtime) {
    return (
      <div className="mt-4 rounded-3xl bg-danger/[0.07] p-4 text-[14px] text-ink">
        {status.reason} Run <code className="rounded bg-ink/[0.06] px-1.5">{status.fix}</code> and restart Jarvis.
      </div>
    );
  }

  const active = pack?.state === "downloading" || pack?.state === "verifying";
  const fraction = pack?.bytes_total ? pack.bytes_done / pack.bytes_total : 0;
  return (
    <div className="mt-4 rounded-3xl bg-accent/[0.07] p-4">
      <div className="flex items-center gap-3">
        <p className="min-w-0 flex-1 text-[14px] text-ink">
          {active
            ? `Getting Kronos… ${pack?.bytes_total ? `${mb(pack.bytes_done)} of ${mb(pack.bytes_total)}` : ""}`
            : pack?.state === "failed"
              ? pack.detail
              : "Forecasting uses Kronos, a 25M-parameter model for price candles. It runs on this PC's processor; the model is about 100 MB, downloaded once from Hugging Face."}
        </p>
        {!active && (
          <Button small icon={Download} onClick={() => void getModel()}>
            {pack?.state === "failed" ? "Try again" : "Get Kronos"}
          </Button>
        )}
      </div>
      {active && (
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink/[0.07]">
          <motion.div className="h-full rounded-full bg-accent" animate={{ width: `${fraction * 100}%` }} transition={GLIDE} />
        </div>
      )}
    </div>
  );
}
