// Preferences live in the database, not only in the window's storage (server/api/prefs.py).
// At start: whatever the server has wins; anything only this window knew (a name typed before this
// existed) is sent up once. After that, every change is saved a moment after it is made.
import { useAppearance } from "../design/theme";
import { useUi } from "./ui";

type Prefs = Partial<{
  name: string;
  think: ReturnType<typeof useUi.getState>["think"];
  devTools: boolean;
  sidebarOpen: boolean;
  mode: ReturnType<typeof useAppearance.getState>["mode"];
  reduceEffects: boolean;
}>;

function current(): Prefs {
  const { name, think, devTools, sidebarOpen } = useUi.getState();
  const { mode, reduceEffects } = useAppearance.getState();
  return { name, think, devTools, sidebarOpen, mode, reduceEffects };
}

const save = (prefs: Prefs) =>
  fetch("/api/prefs", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(prefs) }).catch(
    () => undefined,
  );

export async function syncPrefs(): Promise<void> {
  const saved = (await fetch("/api/prefs")
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null)) as Prefs | null;
  if (saved === null) return; // An older server, or none: the window's storage is all there is.

  const ui = useUi.getState();
  const look = useAppearance.getState();
  if (saved.name !== undefined && saved.name !== ui.name) ui.setName(saved.name);
  if (saved.think !== undefined && saved.think !== ui.think) ui.setThink(saved.think);
  if (saved.devTools !== undefined && saved.devTools !== ui.devTools) ui.setDevTools(saved.devTools);
  if (saved.sidebarOpen !== undefined && saved.sidebarOpen !== ui.sidebarOpen) ui.toggleSidebar();
  if (saved.mode !== undefined && saved.mode !== look.mode) look.setMode(saved.mode);
  if (saved.reduceEffects !== undefined && saved.reduceEffects !== look.reduceEffects) look.setReduceEffects(saved.reduceEffects);

  let last = JSON.stringify(current());
  if (Object.keys(saved).length === 0) void save(current());
  let timer = 0;
  const changed = () => {
    const now = JSON.stringify(current());
    if (now === last) return;
    last = now;
    window.clearTimeout(timer);
    timer = window.setTimeout(() => void save(JSON.parse(now) as Prefs), 400);
  };
  useUi.subscribe(changed);
  useAppearance.subscribe(changed);
}
