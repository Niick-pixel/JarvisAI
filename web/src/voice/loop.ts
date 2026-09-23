// The conversation loop behind voice mode: listen until you stop talking, send what you said,
// read the answer back a sentence at a time as it streams, then listen again.
//
// "Stopped talking" is a short silence after speech, measured on the same mic level that drives
// the orb. Reading back starts after the first sentence, not the last. There is no automatic
// barge-in: with the speakers on, the mic would hear Jarvis and interrupt itself, so interrupting
// is a tap.
import { useCallback, useEffect, useRef, useState } from "react";
import { split } from "../chat/thinking";
import { useSession } from "../store/session";
import { useVoice } from "../store/voice";
import { drive } from "./level";
import { sentences } from "./speech";

const SPEECH_LEVEL = 0.12;
const SILENCE_MS = 1200;
const MAX_TURN_MS = 60_000;

export type LoopState = "listening" | "hearing" | "thinking" | "speaking" | "paused";

export function useVoiceLoop(paused: boolean) {
  const phase = useVoice((s) => s.phase);
  const running = useSession((s) => s.runId !== null);
  const [heard, setHeard] = useState("");
  const [saying, setSaying] = useState("");
  const [speaking, setSpeaking] = useState(false);
  const queue = useRef<string[]>([]);
  const offset = useRef(0);
  const busy = useRef(false);
  const alive = useRef(true);

  const pump = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    setSpeaking(true);
    while (queue.current.length && alive.current) {
      const sentence = queue.current.shift()!;
      const voice = useVoice.getState();
      if (voice.status?.tts.available) {
        setSaying(sentence);
        await voice.speak("voice-mode", sentence);
      } else {
        // Without a voice to speak with, the caption is the whole answer.
        setSaying((shown) => `${shown} ${sentence}`.trim());
      }
    }
    busy.current = false;
    setSpeaking(false);
  }, []);

  const enqueue = useCallback(
    (parts: string[]) => {
      if (!parts.length) return;
      queue.current.push(...parts);
      void pump();
    },
    [pump],
  );

  useEffect(() => {
    alive.current = true;
    // Follow the answer as it streams; what is left when it ends is flushed in one go.
    const unsubscribe = useSession.subscribe((s, prev) => {
      if (s.streamingId && s.streamingText !== prev.streamingText) {
        const { answer, open } = split(s.streamingText);
        if (open) return;
        const { parts, next } = sentences(answer, offset.current, false);
        offset.current = next;
        enqueue(parts);
      }
      if (prev.runId && !s.runId) {
        const { answer } = split(prev.streamingText);
        const { parts } = sentences(answer, offset.current, true);
        offset.current = 0;
        enqueue(parts);
      }
    });
    return () => {
      alive.current = false;
      unsubscribe();
      queue.current = [];
      useVoice.getState().cancel();
      useVoice.getState().hush();
    };
  }, [enqueue]);

  // What you said goes straight into the conversation - there is no box to review it in.
  const dictated = useVoice((s) => s.dictated);
  useEffect(() => {
    if (!dictated) return;
    useVoice.getState().consume();
    setHeard(dictated);
    setSaying("");
    offset.current = 0;
    void useSession.getState().send(dictated);
  }, [dictated]);

  // Listen whenever nothing else is happening.
  useEffect(() => {
    if (paused) {
      if (phase === "listening") useVoice.getState().cancel();
      return;
    }
    if (phase === "idle" && !running && !speaking && queue.current.length === 0) {
      void useVoice.getState().listen();
    }
  }, [phase, running, speaking, paused]);

  // End the turn on a short silence after speech.
  useEffect(() => {
    if (phase !== "listening") return;
    const started = Date.now();
    let spoke = false;
    let lastLoud = started;
    const timer = window.setInterval(() => {
      const now = Date.now();
      if (drive.raw() > SPEECH_LEVEL) {
        spoke = true;
        lastLoud = now;
      }
      if ((spoke && now - lastLoud > SILENCE_MS) || now - started > MAX_TURN_MS) {
        window.clearInterval(timer);
        void useVoice.getState().finish();
      }
    }, 100);
    return () => window.clearInterval(timer);
  }, [phase]);

  const interrupt = useCallback(() => {
    queue.current = [];
    useVoice.getState().hush();
    void useSession.getState().stop();
  }, []);

  const state: LoopState = paused
    ? "paused"
    : speaking
      ? "speaking"
      : running
        ? "thinking"
        : phase === "transcribing"
          ? "hearing"
          : "listening";

  return { state, heard, saying, interrupt };
}
