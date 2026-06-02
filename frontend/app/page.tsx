"use client";

import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { endpoints } from "@/lib/api";

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-panel rounded-lg p-5 border border-white/10">
      <div className="text-gray-400 text-xs uppercase tracking-wide">{label}</div>
      <div className="text-3xl font-semibold mt-2">{value}</div>
    </div>
  );
}

export default function Overview() {
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: endpoints.datasets });
  const sources = useQuery({ queryKey: ["sources"], queryFn: endpoints.sources });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: endpoints.jobs });

  const byStage = (jobs.data ?? []).reduce<Record<string, number>>((acc, j) => {
    acc[j.stage] = (acc[j.stage] ?? 0) + 1;
    return acc;
  }, {});
  const chart = Object.entries(byStage).map(([stage, count]) => ({ stage, count }));

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Overview</h1>
      <div className="grid grid-cols-3 gap-4">
        <Stat label="Datasets" value={datasets.data?.length ?? 0} />
        <Stat label="Sources" value={sources.data?.length ?? 0} />
        <Stat label="Jobs" value={jobs.data?.length ?? 0} />
      </div>
      <div className="bg-panel rounded-lg p-5 border border-white/10">
        <h2 className="text-sm text-gray-400 mb-4">Jobs by stage</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chart}>
            <XAxis dataKey="stage" stroke="#888" fontSize={12} />
            <YAxis stroke="#888" fontSize={12} allowDecimals={false} />
            <Tooltip contentStyle={{ background: "#151821", border: "none" }} />
            <Bar dataKey="count" fill="#5b8cff" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
