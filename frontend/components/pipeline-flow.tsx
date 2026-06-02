"use client";

import { DROPPED_STATUSES, STAGES } from "@/lib/stages";
import { fmtCompact } from "@/lib/format";

// A live fabrication-line view: nine stations, each showing how many documents
// currently rest at that stage's output status. Reads straight from
// /api/stats status_counts.
export function PipelineFlow({ counts }: { counts: Record<string, number> }) {
  const peak = Math.max(1, ...STAGES.map((s) => (s.status ? counts[s.status] ?? 0 : 0)));
  const dropped = DROPPED_STATUSES.reduce((n, s) => n + (counts[s] ?? 0), 0);

  return (
    <div>
      <div className="flex items-stretch gap-1.5 overflow-x-auto pb-2">
        {STAGES.map((stage, i) => {
          const count = stage.status ? counts[stage.status] ?? 0 : null;
          const fill = count != null ? Math.round(((count ?? 0) / peak) * 100) : 0;
          const live = (count ?? 0) > 0;
          return (
            <div key={stage.key} className="flex min-w-[88px] flex-1 items-center gap-1.5">
              <div className="flex-1">
                <div
                  className={`group relative h-[88px] overflow-hidden rounded-md border bg-ink-900/60 px-3 pt-2.5 transition-colors ${
                    live ? "border-signal/30" : "border-[var(--hair)]"
                  }`}
                >
                  {/* fill bar from the bottom */}
                  <div
                    className={`absolute inset-x-0 bottom-0 transition-all duration-700 ${
                      live ? "bg-signal/10" : "bg-white/[0.02]"
                    }`}
                    style={{ height: `${Math.max(fill, 6)}%` }}
                  />
                  <div className="relative">
                    <div className="font-mono text-[10px] text-faint">{stage.index}</div>
                    <div className="mt-1 text-[12px] font-medium text-paper">{stage.label}</div>
                    <div
                      className={`tnum mt-1.5 font-mono text-[15px] ${
                        live ? "text-signal" : "text-faint"
                      }`}
                    >
                      {count == null ? "·" : fmtCompact(count)}
                    </div>
                  </div>
                </div>
              </div>
              {i < STAGES.length - 1 && (
                <span
                  className={`h-px w-3 shrink-0 ${live ? "bg-signal/40" : "bg-[var(--hair)]"}`}
                />
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-4 flex items-center gap-6 border-t border-[var(--hair)] pt-3 font-mono text-[11px]">
        <span className="flex items-center gap-2 text-dim">
          <span className="h-1.5 w-1.5 rounded-full bg-signal" /> active stage
        </span>
        <span className="text-dim">
          dropped (dup + rejected): <span className="tnum text-err">{fmtCompact(dropped)}</span>
        </span>
      </div>
    </div>
  );
}
