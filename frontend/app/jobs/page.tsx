"use client";

import { QueryTable } from "@/components/data-table";
import { endpoints } from "@/lib/api";
import type { Job } from "@/lib/types";

export default function JobsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Jobs</h1>
      <QueryTable<Job>
        queryKey={["jobs"]}
        queryFn={endpoints.jobs}
        columns={[
          { key: "stage", header: "Stage" },
          { key: "status", header: "Status" },
          { key: "attempts", header: "Attempts" },
          { key: "run_id", header: "Run", render: (r) => r.run_id ?? "—" },
          { key: "error", header: "Error", render: (r) => r.error ?? "—" },
          { key: "created_at", header: "Created" },
        ]}
      />
    </div>
  );
}
