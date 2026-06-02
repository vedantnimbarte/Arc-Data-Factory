"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis } from "recharts";

import { DatasetSelect } from "@/components/dataset-select";
import { PipelineFlow } from "@/components/pipeline-flow";
import { PageHeader } from "@/components/ui/page-header";
import { Panel } from "@/components/ui/panel";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { endpoints } from "@/lib/api";
import { fmtCompact, fmtInt, fmtRelative } from "@/lib/format";

export default function Overview() {
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: endpoints.datasets });
  const sources = useQuery({ queryKey: ["sources"], queryFn: endpoints.sources });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: endpoints.jobs });

  const [picked, setPicked] = useState("");
  const datasetId = picked || datasets.data?.[0]?.id || "";
  const stats = useQuery({
    queryKey: ["stats", datasetId],
    queryFn: () => endpoints.stats(datasetId),
    enabled: Boolean(datasetId),
  });

  const byStage = (jobs.data ?? []).reduce<Record<string, number>>((acc, j) => {
    acc[j.stage] = (acc[j.stage] ?? 0) + 1;
    return acc;
  }, {});
  const chart = Object.entries(byStage).map(([stage, count]) => ({ stage, count }));
  const failing = (jobs.data ?? []).filter((j) => ["failed", "dead"].includes(j.status)).length;
  const recent = (jobs.data ?? []).slice(0, 6);

  return (
    <div className="space-y-9">
      <PageHeader
        index="00 · Control"
        title="Overview"
        subtitle="Live telemetry across the ARC fabrication line — sources in, versioned Parquet datasets out."
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Datasets" value={fmtInt(datasets.data?.length ?? 0)} delay={0} />
        <StatCard label="Sources" value={fmtInt(sources.data?.length ?? 0)} delay={60} />
        <StatCard
          label="Tokens"
          value={stats.data ? fmtCompact(stats.data.token_count) : "—"}
          hint={datasetId ? "selected dataset" : "no dataset"}
          accent
          delay={120}
        />
        <StatCard
          label="Jobs"
          value={fmtInt(jobs.data?.length ?? 0)}
          unit={failing ? `· ${failing} failing` : undefined}
          delay={180}
        />
      </div>

      <Panel
        label="Pipeline flow"
        delay={120}
        aside={
          datasets.data?.length ? (
            <DatasetSelect datasets={datasets.data} value={datasetId} onChange={setPicked} />
          ) : null
        }
      >
        {stats.isLoading ? (
          <Skeleton className="h-[120px] w-full" />
        ) : stats.data ? (
          <PipelineFlow counts={stats.data.status_counts} />
        ) : (
          <p className="py-8 text-center text-[13px] text-dim">
            Create a dataset and run the pipeline to see flow telemetry.
          </p>
        )}
      </Panel>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <Panel label="Jobs by stage" className="lg:col-span-3" delay={160}>
          {chart.length ? (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={chart} margin={{ top: 8, right: 0, left: -20, bottom: 0 }}>
                <XAxis
                  dataKey="stage"
                  stroke="#62656c"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
                />
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.03)" }}
                  contentStyle={{
                    background: "#101114",
                    border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: 8,
                    fontSize: 12,
                    fontFamily: "var(--font-plex-mono)",
                  }}
                  labelStyle={{ color: "#9b9d98" }}
                />
                <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                  {chart.map((_, i) => (
                    <Cell key={i} fill="#cdf24e" fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="py-16 text-center text-[13px] text-dim">No jobs enqueued yet.</p>
          )}
        </Panel>

        <Panel label="Recent jobs" className="lg:col-span-2" delay={200}>
          {jobs.isLoading ? (
            <Skeleton className="h-[200px] w-full" />
          ) : recent.length ? (
            <ul className="divide-y divide-[var(--hair)]">
              {recent.map((j) => (
                <li key={j.id} className="flex items-center justify-between py-2.5">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-[12px] text-paper">{j.stage}</span>
                    <span className="font-mono text-[11px] text-faint">{fmtRelative(j.created_at)}</span>
                  </div>
                  <StatusBadge status={j.status} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="py-16 text-center text-[13px] text-dim">Nothing running.</p>
          )}
        </Panel>
      </div>
    </div>
  );
}
