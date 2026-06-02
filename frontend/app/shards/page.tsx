"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { QueryTable } from "@/components/data-table";
import { endpoints } from "@/lib/api";
import type { Shard } from "@/lib/types";

export default function ShardsPage() {
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: endpoints.datasets });
  const [selected, setSelected] = useState<string>("");
  const id = selected || datasets.data?.[0]?.id || "";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Shards</h1>
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

      {id && (
        <QueryTable<Shard>
          queryKey={["shards", id]}
          queryFn={() => endpoints.shards(id)}
          columns={[
            { key: "shard_index", header: "#" },
            { key: "row_count", header: "Rows" },
            { key: "token_count", header: "Tokens" },
            { key: "size_bytes", header: "Bytes" },
            { key: "checksum", header: "Checksum", render: (r) => r.checksum.slice(0, 12) + "…" },
            { key: "path", header: "Path" },
          ]}
          empty="No shards yet."
        />
      )}
    </div>
  );
}
