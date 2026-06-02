import type { ReactNode } from "react";

export function StatCard({
  label,
  value,
  unit,
  hint,
  accent = false,
  delay = 0,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  hint?: ReactNode;
  accent?: boolean;
  delay?: number;
}) {
  return (
    <div
      className="group animate-rise relative overflow-hidden rounded-lg border border-[var(--hair)] bg-ink-800/70 p-5 shadow-panel transition-colors hover:border-[var(--hair-strong)]"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div
        className={`absolute inset-x-0 top-0 h-px origin-left animate-sweep ${
          accent ? "bg-signal" : "bg-[var(--hair-strong)]"
        }`}
        style={{ animationDelay: `${delay + 120}ms` }}
      />
      <div className="font-mono text-[10.5px] uppercase tracking-[0.2em] text-faint">{label}</div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span
          className={`tnum font-display text-[40px] font-semibold leading-none tracking-tightest ${
            accent ? "text-signal" : "text-paper"
          }`}
        >
          {value}
        </span>
        {unit && <span className="font-mono text-[12px] text-faint">{unit}</span>}
      </div>
      {hint && <div className="mt-3 font-mono text-[11px] text-dim">{hint}</div>}
    </div>
  );
}
