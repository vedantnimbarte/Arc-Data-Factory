"use client";

import { QueryTable } from "@/components/data-table";
import { endpoints } from "@/lib/api";
import type { Language } from "@/lib/types";

export default function LanguagesPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Languages</h1>
      <QueryTable<Language>
        queryKey={["languages"]}
        queryFn={endpoints.languages}
        columns={[
          { key: "code", header: "Code" },
          { key: "name", header: "Name" },
        ]}
        empty="No languages registered yet."
      />
    </div>
  );
}
