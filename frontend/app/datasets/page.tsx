"use client";

import { QueryTable } from "@/components/data-table";
import { endpoints } from "@/lib/api";
import type { Dataset } from "@/lib/types";

export default function DatasetsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Datasets</h1>
      <QueryTable<Dataset>
        queryKey={["datasets"]}
        queryFn={endpoints.datasets}
        columns={[
          { key: "name", header: "Name" },
          { key: "version", header: "Version" },
          { key: "status", header: "Status" },
          { key: "parent_id", header: "Parent", render: (r) => r.parent_id ?? "—" },
          { key: "created_at", header: "Created" },
        ]}
      />
    </div>
  );
}
