// The wake word's ear: the microphone at 16 kHz, as 16-bit samples, streamed to the detector on
// this PC over a loopback socket. Nothing is recorded; the socket only ever answers "wake".
import { request } from "../api/client";
import type { WakeStatus } from "../api/types";
import { MicError } from "./mic";

export const wakeApi = {
  status: () => request<WakeStatus>("/api/voice/wake"),
  install: () => request<WakeStatus>("/api/voice/wake/install", { method: "POST" }),
};

export interface Ear {
  stop: () => void;
}

function socketUrl(): string {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${location.host}/api/voice/wake/listen`;
}

export async function listen(onWake: () => void, onError: (message: string) => void): Promise<Ear> {
  if (!navigator.mediaDevices?.getUserMedia) throw new MicError("This browser exposes no microphone API.");
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  });
  // Asking the context for 16 kHz makes the browser resample - the rate the models expect.
  const context = new AudioContext({ sampleRate: 16000 });
  const source = context.createMediaStreamSource(stream);
  const node = context.createScriptProcessor(2048, 1, 1);
  const socket = new WebSocket(socketUrl());
  socket.binaryType = "arraybuffer";
  let stopped = false;

  node.onaudioprocess = (event) => {
    if (socket.readyState !== WebSocket.OPEN) return;
    const input = event.inputBuffer.getChannelData(0);
    const pcm = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) pcm[i] = Math.max(-1, Math.min(1, input[i] ?? 0)) * 0x7fff;
    socket.send(pcm.buffer);
  };
  source.connect(node);
  node.connect(context.destination);

  socket.onmessage = (event) => {
    const data = JSON.parse(String(event.data)) as { wake?: boolean };
    if (data.wake) onWake();
  };
  socket.onclose = (event) => {
    if (!stopped) onError(event.code === 4404 ? "The wake word is not installed." : "The wake word stopped listening.");
  };

  return {
    stop: () => {
      stopped = true;
      node.disconnect();
      source.disconnect();
      void context.close();
      for (const track of stream.getTracks()) track.stop();
      socket.close();
    },
  };
}
