import { AnimatePresence, LayoutGroup, motion } from "framer-motion";
import { useEffect } from "react";
import Approvals from "./agents/Approvals";
import Composer from "./chat/Composer";
import Home from "./chat/Home";
import Thread from "./chat/Thread";
import CaptureCard from "./memory/CaptureCard";
import GetModel from "./models/GetModel";
import Halo from "./shell/Halo";
import ModelPill from "./shell/ModelPill";
import SheetHost from "./shell/SheetHost";
import Sidebar from "./shell/Sidebar";
import Toasts from "./shell/Toasts";
import { useAgents } from "./store/agents";
import { useDownloads } from "./store/downloads";
import { useSession } from "./store/session";
import { useUi } from "./store/ui";
import { useVoice } from "./store/voice";
import { BOUNCE } from "./ui/motion";
import VoiceMode from "./voice/VoiceMode";

export default function App() {
  const bootstrap = useSession((s) => s.bootstrap);
  const hasTurns = useSession((s) => s.activePath.length > 0 || s.streamingId !== null);
  const busy = useSession((s) => s.runId !== null);
  const listening = useVoice((s) => s.phase === "listening");
  const voiceMode = useUi((s) => s.voiceMode);

  useEffect(() => {
    void bootstrap().catch(() => undefined);
    // Asked once, at boot: the answer decides whether the mic explains itself or works.
    void useVoice.getState().refresh().catch(() => undefined);
    // A fresh install has llama.cpp but no model yet: offer one instead of an empty chat.
    void useDownloads.getState().checkFirstRun().catch(() => undefined);
    // Jobs fire while you are elsewhere; this is what makes an approval appear without a reload.
    return useAgents.getState().watch();
  }, [bootstrap]);

  return (
    <div className="flex h-full">
      <Sidebar />
      <main className="relative flex min-w-0 flex-1 flex-col overflow-hidden bg-bg">
        <Halo state={listening ? "listening" : busy ? "busy" : "rest"} placement={hasTurns ? "bottom" : "center"} />
        <header className="relative z-10 flex h-14 shrink-0 items-center px-3">
          <ModelPill />
        </header>
        <LayoutGroup>
          {hasTurns ? (
            <>
              <Thread />
              <div className="relative z-10 mx-auto w-full max-w-[760px] px-6 pb-4">
                <motion.div layoutId="composer" transition={BOUNCE}>
                  <Composer />
                </motion.div>
                <p className="mt-2 text-center text-[12px] text-ink-muted">
                  Runs on this PC. Nothing you say leaves it.
                </p>
              </div>
            </>
          ) : (
            <Home />
          )}
        </LayoutGroup>
      </main>
      <SheetHost />
      <AnimatePresence>{voiceMode && <VoiceMode />}</AnimatePresence>
      <CaptureCard />
      <Approvals />
      <Toasts />
      <GetModel />
    </div>
  );
}
