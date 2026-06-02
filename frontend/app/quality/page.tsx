"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DatasetSelect } from "@/components/dataset-select";
import { PageHeader } from "@/components/ui/page-header";
import { Panel } from "@/components/ui/panel";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { endpoints } from "@/lib/api";
import { fmtCompact, fmtInt } from "@/lib/format";
import { statusTone } from "@/lib/stages";

const TONE_BG: Record<string, string> = {
  ok: "bg-ok",
  run: "bg-run",
  warn: "bg-warn",
  err: "bg-err",
  idle: "bg-idle",
  signal: "bg-signal",
};

function Bars({ data, title }: { data: Record<string, number>; title: string }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const peak = Math.max(1, ...entries.map(([, v]) => v));
  if (!entries.length)
    return <p className="py-8 text-center text-[13px] text-dim">No {title} data.</p>;
  return (
    <div className="space-y-3">
      {entries.map(([k, v]) => (
        <div key={k} className="flex items-center gap-3">
          <div className="w-28 shrink-0 truncate font-mono text-[12px] text-dim">{k}</div>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-900">
            <div
              className={`h-full rounded-full ${TONE_BG[statusTone(k)]} transition-all duration-700`}
              style={{ width: `${Math.max((v / peak) * 100, 3)}%`, opacity: 0.85 }}
            />
          </div>
          <div className="tnum w-16 shrink-0 text-right font-mono text-[12px] text-paper">
            {fmtInt(v)}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function QualityPage() {
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: endpoints.datasets });
  const [picked, setPicked] = useState("");
  const id = picked || datasets.data?.[0]?.id || "";

  const stats = useQuery({
    queryKey: ["stats", id],
    queryFn: () => endpoints.stats(id),
    enabled: Boolean(id),
  });
  const quality = useQuery({
    queryKey: ["quality", id],
    queryFn: () => endpoints.quality(id),
    enabled: Boolean(id),
  });

  return (
    <div className="space-y-9">
      <PageHeader
        index="02 · Monitor"
        title="Quality"
        subtitle="Per-dataset composition: stage distribution, token volume, and language mix."
        actions={
          datasets.data?.length ? (
            <DatasetSelect datasets={datasets.data} value={id} onChange={setPicked} />
          ) : null
        }
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Documents" value={stats.data ? fmtInt(stats.data.document_count) : "—"} />
        <StatCard
          label="Tokens"
          value={stats.data ? fmtCompact(stats.data.token_count) : "—"}
          accent
          delay={60}
        />
        <StatCard
          label="Sharded"
          value={stats.data ? fmtInt(stats.data.status_counts["sharded"] ?? 0) : "—"}
          delay={120}
        />
        <StatCard
          label="Rejected"
          value={
            stats.data
              ? fmtInt(
                  (stats.data.status_counts["rejected"] ?? 0) +
                    (stats.data.status_counts["duplicate"] ?? 0),
                )
              : "—"
          }
          hint="dropped"
          delay={180}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel label="Documents by stage" delay={120}>
          {stats.isLoading ? (
            <Skeleton className="h-[180px] w-full" />
          ) : (
            <Bars data={stats.data?.status_counts ?? {}} title="stage" />
          )}
        </Panel>
        <Panel label="Language mix" delay={160}>
          {quality.isLoading ? (
            <Skeleton className="h-[180px] w-full" />
          ) : (
            <Bars data={quality.data?.languages ?? {}} title="language" />
          )}
        </Panel>
      </div>
    </div>
  );
}
