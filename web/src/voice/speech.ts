// Turning a streaming Markdown answer into speakable sentences, one at a time, so voice mode can
// start talking after the first sentence instead of after the last.

/** Markdown is for eyes. Code is summarised rather than read out symbol by symbol. */
export function speakable(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?(```|$)/g, " I've put the code on screen. ")
    .replace(/`([^`]*)`/g, "$1")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/^\s{0,3}(#{1,6}|>|[-*+]|\d+\.)\s+/gm, "")
    .replace(/[*_~|]+/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

/** Complete sentences in `text` from `from` on, and where the next unread one starts. */
export function sentences(text: string, from: number, final: boolean): { parts: string[]; next: number } {
  const parts: string[] = [];
  const boundary = /[.!?](?=\s)|\n\n/g;
  boundary.lastIndex = from;
  let start = from;
  // Very short fragments ("1.", "e.g.") are joined onto what follows rather than spoken alone.
  for (let match = boundary.exec(text); match; match = boundary.exec(text)) {
    const end = match.index + match[0].length;
    if (end - start < 24) continue;
    parts.push(text.slice(start, end));
    start = end;
  }
  if (final && start < text.length) {
    parts.push(text.slice(start));
    start = text.length;
  }
  return { parts: parts.map(speakable).filter(Boolean), next: start };
}
