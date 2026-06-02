"use client";

import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { SkeletonRows } from "@/components/ui/skeleton";

type Column<T> = {
  key: keyof T | string;
  header: string;
  render?: (row: T) => ReactNode;
  mono?: boolean;
  align?: "left" | "right";
};

export function QueryTable<T extends Record<string, unknown>>({
  queryKey,
  queryFn,
  columns,
  empty = "No rows yet.",
  rowKey,
}: {
  queryKey: string[];
  queryFn: () => Promise<T[]>;
  columns: Column<T>[];
  empty?: string;
  rowKey?: (row: T, i: number) => string;
}) {
  const { data, isLoading, error } = useQuery({ queryKey, queryFn });

  if (isLoading) return <SkeletonRows rows={6} />;
  if (error)
    return (
      <div className="flex items-center gap-2 rounded-md border border-err/30 bg-err/5 px-4 py-3 font-mono text-[12px] text-err">
        <span className="h-1.5 w-1.5 rounded-full bg-err" />
        {(error as Error).message}
      </div>
    );
  if (!data?.length)
    return (
      <div className="grid place-items-center rounded-md border border-dashed border-[var(--hair)] py-14 text-center">
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-faint">no data</div>
        <div className="mt-1.5 text-[13px] text-dim">{empty}</div>
      </div>
    );

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr className="border-b border-[var(--hair-strong)] text-left">
            {columns.map((c) => (
              <th
                key={String(c.key)}
                className={`pb-3 pr-5 font-mono text-[10.5px] font-medium uppercase tracking-[0.16em] text-faint ${
                  c.align === "right" ? "text-right" : ""
                }`}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={rowKey ? rowKey(row, i) : i}
              className="group border-b border-[var(--hair)] transition-colors last:border-0 hover:bg-ink-700/50"
            >
              {columns.map((c) => (
                <td
                  key={String(c.key)}
                  className={`py-3 pr-5 align-middle ${c.align === "right" ? "text-right" : ""} ${
                    c.mono ? "tnum font-mono text-[12.5px] text-dim" : "text-paper/90"
                  }`}
                >
                  {c.render ? c.render(row) : String(row[c.key as keyof T] ?? "—") || "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
