"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DatasetSelect } from "@/components/dataset-select";
import { PageHeader } from "@/components/ui/page-header";
import { Panel } from "@/components/ui/panel";
import { SkeletonRows } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { endpoints } from "@/lib/api";
import { fmtBytes, fmtCompact, fmtInt, shortUri } from "@/lib/format";

export default function ShardsPage() {
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: endpoints.datasets });
  const [picked, setPicked] = useState("");
  const id = picked || datasets.data?.[0]?.id || "";

  const shards = useQuery({
    queryKey: ["shards", id],
    queryFn: () => endpoints.shards(id),
    enabled: Boolean(id),
  });

  const rows = shards.data ?? [];
  const totals = rows.reduce(
    (a, s) => ({
      rows: a.rows + s.row_count,
      tokens: a.tokens + s.token_count,
      bytes: a.bytes + s.size_bytes,
    }),
    { rows: 0, tokens: 0, bytes: 0 },
  );

  return (
    <div className="space-y-9">
      <PageHeader
        index="05 · Catalog"
        title="Shards"
        subtitle="Deterministically-ordered Parquet shards. Each is checksummed for reproducible training reads."
        actions={
          datasets.data?.length ? (
            <DatasetSelect datasets={datasets.data} value={id} onChange={setPicked} />
          ) : null
        }
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Shards" value={fmtInt(rows.length)} />
        <StatCard label="Rows" value={fmtCompact(totals.rows)} delay={60} />
        <StatCard label="Tokens" value={fmtCompact(totals.tokens)} accent delay={120} />
        <StatCard label="Size" value={fmtBytes(totals.bytes)} delay={180} />
      </div>

      <Panel label="Shard index">
        {shards.isLoading ? (
          <SkeletonRows rows={6} />
        ) : rows.length ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr className="border-b border-[var(--hair-strong)] text-left">
                  {["#", "Rows", "Tokens", "Size", "Checksum", "Path"].map((h, i) => (
                    <th
                      key={h}
                      className={`pb-3 pr-5 font-mono text-[10.5px] uppercase tracking-[0.16em] text-faint ${
                        i > 0 && i < 4 ? "text-right" : ""
                      }`}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <tr
                    key={s.id}
                    className="border-b border-[var(--hair)] transition-colors last:border-0 hover:bg-ink-700/50"
                  >
                    <td className="py-3 pr-5 font-mono text-[12.5px] text-signal">
                      {String(s.shard_index).padStart(3, "0")}
                    </td>
                    <td className="tnum py-3 pr-5 text-right font-mono text-[12.5px] text-dim">
                      {fmtInt(s.row_count)}
                    </td>
                    <td className="tnum py-3 pr-5 text-right font-mono text-[12.5px] text-dim">
                      {fmtInt(s.token_count)}
                    </td>
                    <td className="tnum py-3 pr-5 text-right font-mono text-[12.5px] text-dim">
                      {fmtBytes(s.size_bytes)}
                    </td>
                    <td className="py-3 pr-5 font-mono text-[11.5px] text-faint">
                      {s.checksum.slice(0, 12)}…
                    </td>
                    <td className="py-3 pr-5 font-mono text-[12px] text-dim">{shortUri(s.path)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="grid place-items-center py-14 text-center">
            <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-faint">no data</div>
            <div className="mt-1.5 text-[13px] text-dim">
              This dataset has no shards yet — run the pipeline through the shard stage.
            </div>
          </div>
        )}
      </Panel>
    </div>
  );
}
