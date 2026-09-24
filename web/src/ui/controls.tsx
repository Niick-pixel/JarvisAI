// The handful of controls every screen is built from. Pills and circles, one weight of icon, and a
// press that gives a little - nothing else is allowed to invent its own button.
import { motion, useReducedMotion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { BOUNCE, PRESS } from "./motion";

type Tone = "primary" | "secondary" | "ghost" | "danger";

const TONES: Record<Tone, string> = {
  primary: "bg-ink text-bg hover:bg-ink/85",
  secondary: "bg-ink/[0.06] text-ink hover:bg-ink/10",
  ghost: "text-ink-muted hover:bg-ink/[0.06] hover:text-ink",
  danger: "text-danger hover:bg-danger/10",
};

export function Button({
  children,
  onClick,
  tone = "secondary",
  icon: Icon,
  disabled,
  title,
  small,
}: {
  children: ReactNode;
  onClick?: () => void;
  tone?: Tone;
  icon?: LucideIcon;
  disabled?: boolean;
  title?: string;
  small?: boolean;
}) {
  const reduced = useReducedMotion();
  return (
    <motion.button
      type="button"
      title={title}
      onClick={onClick}
      disabled={disabled}
      whileTap={reduced || disabled ? undefined : PRESS}
      transition={BOUNCE}
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full font-medium transition-colors disabled:pointer-events-none disabled:opacity-40 ${
        small ? "h-8 px-3 text-[13px]" : "h-9 px-4 text-sm"
      } ${TONES[tone]}`}
    >
      {Icon && <Icon size={small ? 15 : 16} strokeWidth={1.75} />}
      {children}
    </motion.button>
  );
}

/** A round icon button. The label is required: it is the tooltip and the accessible name. */
export function IconButton({
  icon: Icon,
  label,
  onClick,
  active,
  size = 36,
  tip = "bottom",
  className = "",
  disabled,
}: {
  icon: LucideIcon;
  label: string;
  onClick?: () => void;
  active?: boolean;
  size?: number;
  tip?: "bottom" | "top" | "right" | "none";
  className?: string;
  disabled?: boolean;
}) {
  const reduced = useReducedMotion();
  return (
    <motion.button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      whileTap={reduced || disabled ? undefined : { scale: 0.9 }}
      transition={BOUNCE}
      style={{ width: size, height: size }}
      className={`group/tip relative inline-flex shrink-0 items-center justify-center rounded-full transition-colors disabled:opacity-40 ${
        active ? "bg-accent/12 text-accent" : "text-ink-muted hover:bg-ink/[0.06] hover:text-ink"
      } ${className}`}
    >
      <Icon size={Math.round(size * 0.5)} strokeWidth={1.75} />
      {tip !== "none" && <Tip side={tip}>{label}</Tip>}
    </motion.button>
  );
}

const TIP_SIDE = {
  bottom: "left-1/2 top-full mt-2 -translate-x-1/2",
  top: "left-1/2 bottom-full mb-2 -translate-x-1/2",
  right: "left-full top-1/2 ml-2 -translate-y-1/2",
} as const;

/** A quiet label that appears after a beat of hovering, the way macOS does it. */
export function Tip({ children, side = "bottom" }: { children: ReactNode; side?: keyof typeof TIP_SIDE }) {
  return (
    <span
      role="tooltip"
      className={`pointer-events-none absolute z-50 whitespace-nowrap rounded-lg bg-ink px-2 py-1 text-[12px] font-medium text-bg opacity-0 shadow-float transition-opacity delay-0 group-hover/tip:opacity-100 group-hover/tip:delay-500 ${TIP_SIDE[side]}`}
    >
      {children}
    </span>
  );
}

/** The iOS switch: the knob springs across and overshoots by a hair. */
export function Switch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative h-[26px] w-[44px] shrink-0 rounded-full transition-colors ${
        checked ? "bg-accent" : "bg-ink/15"
      }`}
    >
      <motion.span
        layout
        transition={BOUNCE}
        className={`absolute top-[3px] h-5 w-5 rounded-full bg-white shadow-card ${checked ? "right-[3px]" : "left-[3px]"}`}
      />
    </button>
  );
}

/** A pill of choices with a sliding selection behind the active one. */
export function Segmented<T extends string>({
  id,
  options,
  value,
  onChange,
}: {
  id: string;
  options: { value: T; label: string; icon?: LucideIcon }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="inline-flex rounded-full bg-ink/[0.06] p-1">
      {options.map((option) => {
        const active = option.value === value;
        const Icon = option.icon;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`relative inline-flex h-8 items-center gap-1.5 rounded-full px-3.5 text-[13px] font-medium transition-colors ${
              active ? "text-ink" : "text-ink-faint hover:text-ink"
            }`}
          >
            {active && (
              <motion.span
                layoutId={`seg-${id}`}
                transition={BOUNCE}
                className="absolute inset-0 rounded-full bg-surface shadow-card"
              />
            )}
            <span className="relative inline-flex items-center gap-1.5">
              {Icon && <Icon size={15} strokeWidth={1.75} />}
              {option.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export const FIELD =
  "w-full rounded-2xl border border-ink/10 bg-surface px-4 py-2.5 text-[14px] text-ink outline-none transition-shadow placeholder:text-ink-faint focus:border-accent/50 focus:ring-4 focus:ring-accent/10";

/** A row in a settings-style list: title, a line of explanation, and the control on the right. */
export function Row({
  title,
  detail,
  children,
}: {
  title: string;
  detail?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="flex items-center gap-4 py-3.5">
      <div className="min-w-0 flex-1">
        <p className="text-[14px] font-medium text-ink">{title}</p>
        {detail && <p className="mt-0.5 text-[13px] leading-snug text-ink-faint">{detail}</p>}
      </div>
      {children}
    </div>
  );
}

/** An empty state that says what would be here and how to put it there. */
export function Empty({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-ink/[0.05] text-ink-faint">
        <Icon size={22} strokeWidth={1.5} />
      </span>
      <p className="text-[15px] font-medium text-ink">{title}</p>
      {children && <div className="mt-1 max-w-sm text-[13px] leading-relaxed text-ink-faint">{children}</div>}
    </div>
  );
}
