"use client";

import { QueryTable } from "@/components/data-table";
import { PageHeader } from "@/components/ui/page-header";
import { Panel } from "@/components/ui/panel";
import { StatusBadge } from "@/components/ui/status-badge";
import { endpoints } from "@/lib/api";
import { fmtRelative, shortId } from "@/lib/format";
import type { Job } from "@/lib/types";

export default function JobsPage() {
  return (
    <div>
      <PageHeader
        index="01 · Monitor"
        title="Jobs"
        subtitle="Per-stage execution records. Acks-late + bounded retries; exhausted jobs land in the dead-letter."
      />
      <Panel
        label="Job queue"
        aside={
          <span className="flex items-center gap-2 font-mono text-[11px] text-dim">
            <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-signal" /> auto-refresh 5s
          </span>
        }
      >
        <QueryTable<Job>
          queryKey={["jobs"]}
          queryFn={endpoints.jobs}
          rowKey={(r) => r.id}
          empty="No jobs enqueued yet."
          columns={[
            { key: "stage", header: "Stage", render: (r) => <span className="font-medium">{r.stage}</span> },
            { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
            { key: "attempts", header: "Try", mono: true, align: "right" },
            { key: "run_id", header: "Run", mono: true, render: (r) => shortId(r.run_id) },
            {
              key: "error",
              header: "Error",
              render: (r) =>
                r.error ? (
                  <span className="font-mono text-[11.5px] text-err">{r.error.slice(0, 48)}</span>
                ) : (
                  <span className="text-faint">—</span>
                ),
            },
            { key: "created_at", header: "Created", mono: true, render: (r) => fmtRelative(r.created_at) },
          ]}
        />
      </Panel>
    </div>
  );
}
