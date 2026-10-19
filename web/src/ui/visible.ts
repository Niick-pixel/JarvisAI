// Timers that rest while the window is hidden or minimised: a poll nobody can see is wasted work,
// and on a busy machine it competes with the model for the CPU.
export function whenVisible(fn: () => void): () => void {
  return () => {
    if (document.visibilityState !== "hidden") fn();
  };
}
