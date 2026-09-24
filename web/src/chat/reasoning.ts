// The same split the server makes (server/chat/thinking.py): a reasoning model's `<think>` text is
// shown behind a disclosure, never as part of the answer. Two shapes: the model opens the tag
// itself, or the template opened it and only `</think>` appears.
const OPEN = "<think>";
const CLOSE = "</think>";

export interface Split {
  thinking: string;
  answer: string;
  /** True mid-stream, while the model is still inside its thinking. */
  open: boolean;
}

export function split(text: string): Split {
  const close = text.indexOf(CLOSE);
  if (close !== -1 && !text.slice(0, close).includes(OPEN)) {
    return { thinking: text.slice(0, close).trim(), answer: text.slice(close + CLOSE.length).trimStart(), open: false };
  }
  const start = text.indexOf(OPEN);
  if (start === -1) return { thinking: "", answer: text, open: false };
  const end = text.indexOf(CLOSE, start);
  if (end === -1) {
    return { thinking: text.slice(start + OPEN.length).trim(), answer: text.slice(0, start).trimEnd(), open: true };
  }
  return {
    thinking: text.slice(start + OPEN.length, end).trim(),
    answer: (text.slice(0, start) + text.slice(end + CLOSE.length)).trim(),
    open: false,
  };
}
