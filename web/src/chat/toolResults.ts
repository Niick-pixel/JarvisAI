// Reading back what compose.results_message wrote: one envelope per tool that ran, one line per
// call that did not. Plain functions, so they test without a DOM.
import type { Message } from "../api/types";

const ENVELOPE = /<context source="tool:(\S+) ([^"]*)">\n([\s\S]*?)\n<\/context>/g;
const SKIPPED = /^tool:(\S+) (.*?) did not run: (.*?)\. Continue without it\.$/gm;

export const isToolResult = (message: Message) =>
  message.role === "user" && (message.content.includes('<context source="tool:') || /^tool:\S+ .* did not run:/m.test(message.content));

export interface Outcome {
  tool: string;
  target: string;
  output: string;
  ran: boolean;
}

export function outcomes(content: string): Outcome[] {
  const found: Outcome[] = [];
  for (const [, tool = "", target = "", output = ""] of content.matchAll(ENVELOPE)) found.push({ tool, target, output, ran: true });
  for (const [, tool = "", target = "", output = ""] of content.matchAll(SKIPPED)) found.push({ tool, target, output, ran: false });
  return found;
}

/** The model's own call block. The approval card and the result row already say it, readably. */
export const withoutCalls = (text: string) => text.replace(/```tool\s*\n[\s\S]*?(```|$)/g, "").trimEnd();
