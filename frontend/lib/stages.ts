// Canonical pipeline metadata, mirrored from arc/db/enums.py.

export type StageMeta = {
  key: string;
  label: string;
  index: string; // two-digit station number
  status: string | null; // the DocStatus a document holds once this stage finishes
};

export const STAGES: StageMeta[] = [
  { key: "collect", label: "Collect", index: "01", status: "raw" },
  { key: "clean", label: "Clean", index: "02", status: "cleaned" },
  { key: "dedupe", label: "Dedupe", index: "03", status: "unique" },
  { key: "compliance", label: "Compliance", index: "04", status: "compliant" },
  { key: "classify", label: "Classify", index: "05", status: "classified" },
  { key: "score", label: "Score", index: "06", status: "scored" },
  { key: "tokenize", label: "Tokenize", index: "07", status: "tokenized" },
  { key: "shard", label: "Shard", index: "08", status: "sharded" },
  { key: "register", label: "Register", index: "09", status: null },
];

// Maps any status string to a semantic color token (Tailwind text-/bg- suffix).
export function statusTone(status: string): "ok" | "run" | "warn" | "err" | "idle" | "signal" {
  const s = status.toLowerCase();
  if (["succeeded", "ready", "sharded", "compliant"].includes(s)) return "ok";
  if (["running", "building", "tokenized", "classified", "scored", "unique", "cleaned"].includes(s))
    return "run";
  if (["queued", "pending", "retrying", "raw", "draft", "paused"].includes(s)) return "warn";
  if (["failed", "dead", "rejected", "duplicate", "cancelled"].includes(s)) return "err";
  return "idle";
}

export const DROPPED_STATUSES = ["duplicate", "rejected"];
