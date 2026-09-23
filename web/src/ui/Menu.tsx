// A popover menu: it grows out of the thing you clicked, with a small bounce, and goes away on a
// click anywhere else or Escape. Used for the model pill, the composer's "+", and "more".
import { AnimatePresence, motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { Check } from "lucide-react";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { BOUNCE } from "./motion";

export interface MenuItem {
  key: string;
  label: string;
  detail?: string;
  icon?: LucideIcon;
  checked?: boolean;
  danger?: boolean;
  onSelect: () => void;
}

type Place = "bottom-start" | "bottom-end" | "top-start" | "top-end";

const PLACE: Record<Place, { className: string; origin: string }> = {
  "bottom-start": { className: "left-0 top-full mt-2", origin: "top left" },
  "bottom-end": { className: "right-0 top-full mt-2", origin: "top right" },
  "top-start": { className: "left-0 bottom-full mb-2", origin: "bottom left" },
  "top-end": { className: "right-0 bottom-full mb-2", origin: "bottom right" },
};

export default function Menu({
  trigger,
  items,
  header,
  footer,
  place = "bottom-start",
  width = 280,
}: {
  trigger: (open: boolean, toggle: () => void) => ReactNode;
  items: MenuItem[];
  header?: ReactNode;
  footer?: ReactNode;
  place?: Place;
  width?: number;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const { className, origin } = PLACE[place];
  return (
    <div ref={root} className="relative">
      {trigger(open, () => setOpen((value) => !value))}
      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            initial={{ opacity: 0, scale: 0.92, y: place.startsWith("top") ? 6 : -6 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, transition: { duration: 0.12 } }}
            transition={BOUNCE}
            style={{ width, transformOrigin: origin }}
            className={`absolute z-50 max-h-[70vh] overflow-y-auto rounded-3xl border border-ink/[0.06] bg-raised p-1.5 shadow-float scroll-quiet ${className}`}
          >
            {header}
            {items.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.key}
                  role="menuitem"
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    item.onSelect();
                  }}
                  className={`flex w-full items-start gap-3 rounded-2xl px-3 py-2.5 text-left transition-colors hover:bg-ink/[0.05] ${
                    item.danger ? "text-danger" : "text-ink"
                  }`}
                >
                  {Icon && <Icon size={18} strokeWidth={1.75} className="mt-px shrink-0 opacity-80" />}
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[14px]">{item.label}</span>
                    {item.detail && (
                      <span className="mt-0.5 block text-[12px] leading-snug text-ink-faint">{item.detail}</span>
                    )}
                  </span>
                  {item.checked && <Check size={17} strokeWidth={2} className="mt-px shrink-0 text-accent" />}
                </button>
              );
            })}
            {footer}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
