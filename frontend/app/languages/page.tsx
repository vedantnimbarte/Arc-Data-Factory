"use client";

import { QueryTable } from "@/components/data-table";
import { PageHeader } from "@/components/ui/page-header";
import { Panel } from "@/components/ui/panel";
import { endpoints } from "@/lib/api";
import type { Language } from "@/lib/types";

export default function LanguagesPage() {
  return (
    <div>
      <PageHeader
        index="06 · Catalog"
        title="Languages"
        subtitle="Detected during cleaning (ISO 639-1). Backs per-dataset language breakdowns."
      />
      <Panel label="Supported languages">
        <QueryTable<Language>
          queryKey={["languages"]}
          queryFn={endpoints.languages}
          rowKey={(r) => r.code}
          empty="No languages registered yet."
          columns={[
            { key: "code", header: "Code", mono: true, render: (r) => r.code.toUpperCase() },
            { key: "name", header: "Name" },
          ]}
        />
      </Panel>
    </div>
  );
}
