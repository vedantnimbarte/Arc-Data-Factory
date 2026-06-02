"use client";

import { QueryTable } from "@/components/data-table";
import { endpoints } from "@/lib/api";
import type { Source } from "@/lib/types";

export default function SourcesPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Sources</h1>
      <QueryTable<Source>
        queryKey={["sources"]}
        queryFn={endpoints.sources}
        columns={[
          { key: "name", header: "Name" },
          { key: "type", header: "Type" },
          { key: "url", header: "URL" },
          { key: "enabled", header: "Enabled", render: (r) => (r.enabled ? "yes" : "no") },
          { key: "last_synced_at", header: "Last synced", render: (r) => r.last_synced_at ?? "never" },
        ]}
      />
    </div>
  );
}
