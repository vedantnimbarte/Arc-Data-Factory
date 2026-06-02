"use client";

import { QueryTable } from "@/components/data-table";
import { PageHeader } from "@/components/ui/page-header";
import { Panel } from "@/components/ui/panel";
import { endpoints } from "@/lib/api";
import { fmtRelative } from "@/lib/format";
import type { Source } from "@/lib/types";

export default function SourcesPage() {
  return (
    <div>
      <PageHeader
        index="04 · Catalog"
        title="Sources"
        subtitle="Ingestion endpoints — GitHub, GitLab, SourceHut, RFCs, docs, Wikipedia, and web datasets."
      />
      <Panel label="Registered sources">
        <QueryTable<Source>
          queryKey={["sources"]}
          queryFn={endpoints.sources}
          rowKey={(r) => r.id}
          empty="No sources yet — register one via POST /api/sources."
          columns={[
            { key: "name", header: "Name", render: (r) => <span className="font-medium">{r.name}</span> },
            {
              key: "type",
              header: "Type",
              render: (r) => (
                <span className="rounded border border-[var(--hair)] bg-ink-900/60 px-2 py-0.5 font-mono text-[11px] text-dim">
                  {r.type}
                </span>
              ),
            },
            { key: "url", header: "URL", mono: true },
            {
              key: "enabled",
              header: "State",
              render: (r) => (
                <span className={`font-mono text-[12px] ${r.enabled ? "text-ok" : "text-faint"}`}>
                  {r.enabled ? "● enabled" : "○ disabled"}
                </span>
              ),
            },
            {
              key: "last_synced_at",
              header: "Last sync",
              mono: true,
              render: (r) => (r.last_synced_at ? fmtRelative(r.last_synced_at) : "never"),
            },
          ]}
        />
      </Panel>
    </div>
  );
}
