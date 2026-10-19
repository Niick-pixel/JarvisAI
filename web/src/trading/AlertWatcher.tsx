// Alerts reach you wherever you are in the app: a toast, and - if you turned it on - read aloud.
// It asks the backend every 15 seconds, which against loopback costs nothing.
import { useEffect, useRef } from "react";
import { tradingApi } from "../api/trading";
import { toast } from "../store/toast";
import { useTrading } from "../store/trading";
import { useVoice } from "../store/voice";

export default function AlertWatcher() {
  const seen = useRef<number | null>(null);
  useEffect(() => {
    const check = async () => {
      const live = await tradingApi.live().catch(() => null);
      if (!live) return;
      const newest = live.events[0]?.created_at ?? 0;
      if (seen.current === null) {
        seen.current = newest; // what was there before you opened the app is not news
        return;
      }
      const fresh = live.events
        .filter((e) => e.created_at > (seen.current ?? 0))
        .reverse();
      seen.current = Math.max(seen.current, newest);
      for (const event of fresh) {
        toast(event.message);
        if (useTrading.getState().speakAlerts)
          void useVoice.getState().speak(event.id, event.message);
      }
    };
    void check();
    const timer = window.setInterval(() => void check(), 15_000);
    return () => window.clearInterval(timer);
  }, []);
  return null;
}
