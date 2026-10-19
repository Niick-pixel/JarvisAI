// The desktop hotkey's landing: Ctrl+Shift+Space captured the screen; this opens a fresh chat
// with the screenshot attached and the cursor waiting for your question.
import { useEffect } from "react";
import type { Attachment } from "../api/types";
import { useAttachments } from "../store/attachments";
import { useSession } from "../store/session";
import { useUi } from "../store/ui";

declare global {
  interface Window {
    __jarvisScreen?: (attachment: Attachment) => void;
  }
}

export default function ScreenHotkey() {
  useEffect(() => {
    window.__jarvisScreen = (attachment) => {
      useUi.getState().closeSheet();
      useSession.getState().newChat();
      useAttachments.getState().add(attachment);
      window.setTimeout(() => document.querySelector<HTMLTextAreaElement>("textarea")?.focus(), 50);
    };
    return () => {
      delete window.__jarvisScreen;
    };
  }, []);
  return null;
}
