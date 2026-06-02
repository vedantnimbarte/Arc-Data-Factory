"use client";

import { QueryTable } from "@/components/data-table";
import { PageHeader } from "@/components/ui/page-header";
import { Panel } from "@/components/ui/panel";
import { StatusBadge } from "@/components/ui/status-badge";
import { endpoints } from "@/lib/api";
import { fmtRelative, shortId } from "@/lib/format";
import type { Dataset } from "@/lib/types";

export default function DatasetsPage() {
  return (
    <div>
      <PageHeader
        index="03 · Catalog"
        title="Datasets"
        subtitle="Versioned, reproducible outputs. Each carries lineage and a manifest pinning shards + tokenizer."
      />
      <Panel label="All datasets">
        <QueryTable<Dataset>
          queryKey={["datasets"]}
          queryFn={endpoints.datasets}
          rowKey={(r) => r.id}
          empty="No datasets yet — create one via POST /api/datasets."
          columns={[
            { key: "name", header: "Name", render: (r) => <span className="font-medium">{r.name}</span> },
            { key: "version", header: "Version", mono: true },
            { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
            {
              key: "parent_id",
              header: "Lineage",
              mono: true,
              render: (r) => (r.parent_id ? `↳ ${shortId(r.parent_id)}` : "root"),
            },
            {
              key: "manifest_uri",
              header: "Manifest",
              mono: true,
              render: (r) =>
                r.manifest_uri ? <span className="text-ok">ready</span> : <span className="text-faint">—</span>,
            },
            { key: "created_at", header: "Created", mono: true, render: (r) => fmtRelative(r.created_at) },
          ]}
        />
      </Panel>
    </div>
  );
}
