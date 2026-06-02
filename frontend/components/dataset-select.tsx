"use client";

import type { Dataset } from "@/lib/types";

export function DatasetSelect({
  datasets,
  value,
  onChange,
}: {
  datasets: Dataset[] | undefined;
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="relative inline-flex items-center">
      <span className="pointer-events-none absolute left-3 font-mono text-[10px] uppercase tracking-[0.18em] text-faint">
        dataset
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none rounded-md border border-[var(--hair)] bg-ink-800 py-2 pl-[72px] pr-9 font-mono text-[12.5px] text-paper outline-none transition-colors hover:border-[var(--hair-strong)] focus:border-signal/50"
      >
        {(datasets ?? []).map((d) => (
          <option key={d.id} value={d.id} className="bg-ink-800">
            {d.name} · {d.version}
          </option>
        ))}
      </select>
      <span className="pointer-events-none absolute right-3 text-faint">▾</span>
    </div>
  );
}
