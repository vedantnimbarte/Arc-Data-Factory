"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { endpoints } from "@/lib/api";

export default function QualityPage() {
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: endpoints.datasets });
  const [selected, setSelected] = useState<string>("");

  const id = selected || datasets.data?.[0]?.id || "";
  const stats = useQuery({
    queryKey: ["stats", id],
    queryFn: () => endpoints.stats(id),
    enabled: Boolean(id),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Quality</h1>
      <select
        className="bg-panel border border-white/10 rounded px-3 py-2 text-sm"
        value={id}
        onChange={(e) => setSelected(e.target.value)}
      >
        {(datasets.data ?? []).map((d) => (
          <option key={d.id} value={d.id}>
            {d.name} {d.version}
          </option>
        ))}
      </select>

      {stats.data && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-panel rounded-lg p-5 border border-white/10">
            <div className="text-gray-400 text-xs uppercase">Documents</div>
            <div className="text-2xl font-semibold">{stats.data.document_count}</div>
          </div>
          <div className="bg-panel rounded-lg p-5 border border-white/10">
            <div className="text-gray-400 text-xs uppercase">Tokens</div>
            <div className="text-2xl font-semibold">{stats.data.token_count.toLocaleString()}</div>
          </div>
          <div className="col-span-2 bg-panel rounded-lg p-5 border border-white/10">
            <div className="text-gray-400 text-xs uppercase mb-2">Documents by stage</div>
            <ul className="text-sm space-y-1">
              {Object.entries(stats.data.status_counts).map(([k, v]) => (
                <li key={k} className="flex justify-between">
                  <span className="text-gray-300">{k}</span>
                  <span>{v}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
