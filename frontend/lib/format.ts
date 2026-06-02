// Presentation helpers for telemetry data.

export const fmtInt = (n: number | null | undefined): string =>
  n == null ? "—" : n.toLocaleString("en-US");

export function fmtBytes(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(Math.floor(Math.log(n) / Math.log(1024)), units.length - 1);
  const v = n / 1024 ** i;
  return `${v >= 100 || i === 0 ? Math.round(v) : v.toFixed(1)} ${units[i]}`;
}

export function fmtCompact(n: number | null | undefined): string {
  if (n == null) return "—";
  return Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

export function fmtRelative(iso: string | null | undefined): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const diff = Date.now() - then;
  const s = Math.round(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  return `${d}d ago`;
}

export const shortId = (id: string | null | undefined): string =>
  !id ? "—" : id.length <= 10 ? id : `${id.slice(0, 8)}`;

export const shortUri = (uri: string | null | undefined): string => {
  if (!uri) return "—";
  const parts = uri.replace("s3://", "").split("/");
  return parts.length > 2 ? `…/${parts.slice(-1)[0]}` : uri;
};
