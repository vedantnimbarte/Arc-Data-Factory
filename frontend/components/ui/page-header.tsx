import type { ReactNode } from "react";

export function PageHeader({
  index,
  title,
  subtitle,
  actions,
}: {
  index: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-9 flex items-end justify-between gap-6">
      <div className="animate-rise">
        <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.28em] text-signal-dim">
          {index}
        </div>
        <h1 className="font-display text-[34px] font-bold leading-none tracking-tightest text-paper">
          {title}
        </h1>
        {subtitle && <p className="mt-3 max-w-xl text-[14px] leading-relaxed text-dim">{subtitle}</p>}
      </div>
      {actions && <div className="animate-rise shrink-0" style={{ animationDelay: "80ms" }}>{actions}</div>}
    </div>
  );
}
