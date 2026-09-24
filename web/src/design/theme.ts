// Light or dark, applied as CSS variables before the first frame.
//
// This module runs at import time (main.tsx imports it before rendering), so the page never
// flashes the wrong theme. Light is the default: that was the choice, with dark one tap away in
// Settings and "follow Windows" for anyone who wants the app to change with the time of day.
import { create } from "zustand";
import tokens from "./tokens.json";

export type ThemeMode = "light" | "dark" | "system";
type Palette = Record<string, string>;

const KEY = "jarvis.appearance";

interface Stored {
  mode: ThemeMode;
  reduceEffects: boolean;
}

function load(): Stored {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { mode: "light", reduceEffects: false, ...(JSON.parse(raw) as Partial<Stored>) };
  } catch {
    // Blocked storage must never stop the app from starting.
  }
  return { mode: "light", reduceEffects: false };
}

function systemDark(): boolean {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

export function resolve(mode: ThemeMode): "light" | "dark" {
  return mode === "system" ? (systemDark() ? "dark" : "light") : mode;
}

function triplet(hex: string): string {
  const value = parseInt(hex.slice(1), 16);
  return `${(value >> 16) & 255} ${(value >> 8) & 255} ${value & 255}`;
}

function apply(mode: ThemeMode): void {
  const which = resolve(mode);
  const palette = (tokens as unknown as Record<string, Palette>)[which]!;
  const root = document.documentElement;
  for (const [name, hex] of Object.entries(palette)) root.style.setProperty(`--c-${name}`, triplet(hex));
  root.dataset.theme = which;
  root.style.colorScheme = which;
}

interface AppearanceState extends Stored {
  setMode: (mode: ThemeMode) => void;
  setReduceEffects: (value: boolean) => void;
}

export const useAppearance = create<AppearanceState>((set, get) => ({
  ...load(),
  setMode: (mode) => {
    set({ mode });
    apply(mode);
    persist(get());
  },
  setReduceEffects: (reduceEffects) => {
    set({ reduceEffects });
    persist(get());
  },
}));

function persist(state: Stored): void {
  try {
    localStorage.setItem(KEY, JSON.stringify({ mode: state.mode, reduceEffects: state.reduceEffects }));
  } catch {
    // Nothing here is worth failing over.
  }
}

apply(useAppearance.getState().mode);
window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener("change", () => {
  if (useAppearance.getState().mode === "system") apply("system");
});
