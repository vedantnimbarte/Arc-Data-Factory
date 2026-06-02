// Typed fetch client for the ARC API. The API key is injected from env on the
// server proxy in production; for dev the gateway is open.
const API_KEY = process.env.NEXT_PUBLIC_ARC_API_KEY;

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} -> ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const endpoints = {
  datasets: () => api<import("./types").Dataset[]>("/api/datasets"),
  sources: () => api<import("./types").Source[]>("/api/sources"),
  jobs: () => api<import("./types").Job[]>("/api/jobs"),
  languages: () => api<import("./types").Language[]>("/api/languages"),
  stats: (id: string) => api<import("./types").DatasetStats>(`/api/stats/${id}`),
  shards: (id: string) => api<import("./types").Shard[]>(`/api/datasets/${id}/shards`),
};
