import { statusTone } from "@/lib/stages";

const TONE: Record<string, { dot: string; text: string; ring: string }> = {
  ok: { dot: "bg-ok", text: "text-ok", ring: "border-ok/30" },
  run: { dot: "bg-run", text: "text-run", ring: "border-run/30" },
  warn: { dot: "bg-warn", text: "text-warn", ring: "border-warn/30" },
  err: { dot: "bg-err", text: "text-err", ring: "border-err/30" },
  idle: { dot: "bg-idle", text: "text-dim", ring: "border-[var(--hair)]" },
  signal: { dot: "bg-signal", text: "text-signal", ring: "border-signal/30" },
};

export function StatusBadge({ status }: { status: string }) {
  const t = TONE[statusTone(status)];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${t.ring} bg-ink-900/60 px-2.5 py-0.5 font-mono text-[11px] ${t.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${t.dot}`} />
      {status}
    </span>
  );
}
