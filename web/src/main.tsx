import React from "react";
import { createRoot } from "react-dom/client";
// First: sets the theme's colours before anything paints, so there is never a flash of the wrong one.
import "./design/theme";
import App from "./App";
import "./index.css";
import { syncPrefs } from "./store/prefs";

// Anything that escapes React still reaches jarvis.log, so a crash leaves a trace to send.
function report(where: string, error: unknown) {
  const message =
    error instanceof Error
      ? String(error.stack || error.message)
      : String(error);
  void fetch("/api/client-errors", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ where, message: message.slice(0, 8000) }),
  }).catch(() => undefined);
}
window.addEventListener("error", (e) => report("window", e.error ?? e.message));
window.addEventListener("unhandledrejection", (e) =>
  report("promise", e.reason),
);

void syncPrefs();

const container = document.getElementById("root");
if (!container) throw new Error("#root is missing from index.html");

createRoot(container).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
