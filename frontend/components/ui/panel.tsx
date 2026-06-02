import type { ReactNode } from "react";

export function Panel({
  children,
  className = "",
  label,
  aside,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  label?: string;
  aside?: ReactNode;
  delay?: number;
}) {
  return (
    <section
      className={`animate-rise rounded-lg border border-[var(--hair)] bg-ink-800/70 shadow-panel ${className}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      {(label || aside) && (
        <header className="flex items-center justify-between border-b border-[var(--hair)] px-5 py-3.5">
          {label && (
            <h2 className="font-mono text-[11px] uppercase tracking-[0.2em] text-dim">{label}</h2>
          )}
          {aside}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}
