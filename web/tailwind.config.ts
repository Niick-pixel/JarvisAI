import type { Config } from "tailwindcss";

// Every colour is a CSS variable set by src/design/theme.ts from tokens.json, so one class works
// in both themes and translucency is Tailwind's alpha syntax (`border-ink/10`) on the same token.
const token = (name: string) => `rgb(var(--c-${name}) / <alpha-value>)`;
const names = [
  "bg", "sidebar", "surface", "raised", "bubble", "code", "ink", "ink-muted", "ink-faint",
  "accent", "on-accent", "danger", "success", "glow-a", "glow-b", "glow-c", "grad-a", "grad-b", "grad-c",
];

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: Object.fromEntries(names.map((n) => [n, token(n)])),
      fontFamily: {
        // System faces only: nothing is fetched (rule 0.11), and Segoe UI Variable on Windows and
        // SF Pro on a Mac are better than anything a web font would add.
        sans: [
          '"Segoe UI Variable Text"', '"Segoe UI"', "-apple-system", "BlinkMacSystemFont",
          '"SF Pro Text"', '"Helvetica Neue"', "Inter", "system-ui", "sans-serif",
        ],
        display: [
          '"Segoe UI Variable Display"', '"Segoe UI"', "-apple-system", '"SF Pro Display"',
          "system-ui", "sans-serif",
        ],
        mono: ['"Cascadia Code"', "ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgb(0 0 0 / 0.04), 0 4px 16px rgb(0 0 0 / 0.04)",
        float: "0 2px 6px rgb(0 0 0 / 0.06), 0 12px 40px rgb(0 0 0 / 0.10)",
      },
      borderRadius: { "4xl": "28px" },
    },
  },
  plugins: [],
} satisfies Config;
