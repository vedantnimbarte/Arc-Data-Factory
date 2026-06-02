// Mirrors arc/api/schemas.py response models.
export type Dataset = {
  id: string;
  name: string;
  version: string;
  status: string;
  parent_id: string | null;
  manifest_uri: string | null;
  created_at: string;
};

export type Source = {
  id: string;
  name: string;
  type: string;
  url: string;
  enabled: boolean;
  last_synced_at: string | null;
  created_at: string;
};

export type Job = {
  id: string;
  run_id: string | null;
  stage: string;
  status: string;
  attempts: number;
  error: string | null;
  created_at: string;
};

export type DatasetStats = {
  dataset_id: string;
  status_counts: Record<string, number>;
  token_count: number;
  document_count: number;
};

export type Language = { code: string; name: string };

export type Shard = {
  id: string;
  dataset_id: string;
  shard_index: number;
  path: string;
  size_bytes: number;
  row_count: number;
  token_count: number;
  checksum: string;
};
