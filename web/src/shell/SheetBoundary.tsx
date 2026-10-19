// A sheet that throws while rendering takes only itself down: the chat, the sidebar and the rest
// of the app keep running, and the error is shown and sent to the log instead of a blank window.
import { Component, type ReactNode } from "react";
import { useUi } from "../store/ui";

interface Props {
  name: string;
  children: ReactNode;
}

export default class SheetBoundary extends Component<
  Props,
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error) {
    console.error(`The ${this.props.name} sheet failed to render`, error);
    void fetch("/api/client-errors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        where: `sheet:${this.props.name}`,
        message: String(error.stack || error),
      }),
    }).catch(() => undefined);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div
        role="alert"
        className="fixed inset-x-4 top-20 z-50 mx-auto max-w-lg rounded-3xl bg-surface p-5 shadow-xl"
      >
        <p className="font-medium text-ink">
          The {this.props.name} panel hit an error and was closed safely.
        </p>
        <p className="mt-1 break-words font-mono text-[12px] text-ink-faint">
          {error.message}
        </p>
        <button
          type="button"
          className="mt-3 font-medium text-accent hover:underline"
          onClick={() => useUi.getState().closeSheet()}
        >
          Close
        </button>
      </div>
    );
  }
}
