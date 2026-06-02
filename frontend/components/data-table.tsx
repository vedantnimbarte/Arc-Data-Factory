"use client";

import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";

type Column<T> = { key: keyof T | string; header: string; render?: (row: T) => ReactNode };

export function QueryTable<T extends Record<string, unknown>>({
  queryKey,
  queryFn,
  columns,
  empty = "No rows.",
}: {
  queryKey: string[];
  queryFn: () => Promise<T[]>;
  columns: Column<T>[];
  empty?: string;
}) {
  const { data, isLoading, error } = useQuery({ queryKey, queryFn });

  if (isLoading) return <p className="text-gray-400">Loading…</p>;
  if (error) return <p className="text-red-400">{(error as Error).message}</p>;
  if (!data?.length) return <p className="text-gray-400">{empty}</p>;

  return (
    <table className="w-full text-sm border-collapse">
      <thead>
        <tr className="text-left text-gray-400 border-b border-white/10">
          {columns.map((c) => (
            <th key={String(c.key)} className="py-2 pr-4 font-medium">
              {c.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, i) => (
          <tr key={i} className="border-b border-white/5">
            {columns.map((c) => (
              <td key={String(c.key)} className="py-2 pr-4">
                {c.render ? c.render(row) : String(row[c.key as keyof T] ?? "—")}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
