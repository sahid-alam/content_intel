import { z } from "zod";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, { cache: "no-store", ...init });
  if (!res.ok) throw new Error(`API ${path} returned ${res.status}`);
  return res.json() as Promise<T>;
}

// ─── Health ───

export type HealthResponse = { status: string };

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

// ─── Feed ───

export const ItemSchema = z.object({
  id: z.number(),
  external_id: z.string(),
  source: z.string(),
  subreddit: z.string().nullable(),
  author: z.string(),
  title: z.string(),
  body: z.string(),
  url: z.string(),
  score: z.number(),
  num_comments: z.number(),
  created_utc: z.string(),
  fetched_at: z.string(),
  content_hash: z.string(),
  tag: z.string().nullish().transform((v) => v ?? undefined),
});

export const FeedResponseSchema = z.object({
  items: z.array(ItemSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export type Item = z.infer<typeof ItemSchema>;
export type FeedResponse = z.infer<typeof FeedResponseSchema>;

export async function getFeed(params?: {
  source?: string;
  tag?: string;
  limit?: number;
  offset?: number;
}): Promise<FeedResponse> {
  const qs = new URLSearchParams();
  if (params?.source) qs.set("source", params.source);
  if (params?.tag) qs.set("tag", params.tag);
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));
  const query = qs.toString() ? `?${qs.toString()}` : "";
  const data = await apiFetch<unknown>(`/feed${query}`);
  return FeedResponseSchema.parse(data);
}

// ─── Sync ───

export const SyncResultSchema = z.object({
  fetched: z.number(),
  inserted: z.number(),
  skipped: z.number(),
  source: z.string(),
});

export type SyncResult = z.infer<typeof SyncResultSchema>;

export async function triggerSync(): Promise<SyncResult[]> {
  const data = await apiFetch<unknown>("/sync", { method: "POST" });
  return z.array(SyncResultSchema).parse(data);
}

// ─── Usage ───

export const UsageSchema = z.object({ calls_today: z.number() });
export type Usage = z.infer<typeof UsageSchema>;

export async function getTodayUsage(): Promise<Usage> {
  const data = await apiFetch<unknown>("/feed/usage");
  return UsageSchema.parse(data);
}

// ─── Leads ───

export const LeadSchema = z.object({
  assignment_id: z.number(),
  lead_id: z.number(),
  item_id: z.number(),
  title: z.string(),
  url: z.string(),
  source: z.string(),
  subreddit: z.string().nullable(),
  author: z.string(),
  external_id: z.string(),
  created_utc: z.string(),
  what_they_want: z.string(),
  budget_signal: z.enum(["none", "mentioned", "explicit"]),
  urgency_signal: z.enum(["none", "mentioned", "explicit"]),
  score: z.number(),
  contact_hint: z.string().nullable(),
  status: z.enum(["new", "reviewing", "contacted", "closed"]),
  notes: z.string(),
  contacted_at: z.string().nullable(),
});

export const LeadsResponseSchema = z.object({
  leads: z.array(LeadSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export type Lead = z.infer<typeof LeadSchema>;
export type LeadsResponse = z.infer<typeof LeadsResponseSchema>;

export async function getLeads(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<LeadsResponse> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));
  const query = qs.toString() ? `?${qs.toString()}` : "";
  const data = await apiFetch<unknown>(`/leads${query}`);
  return LeadsResponseSchema.parse(data);
}

export async function patchAssignment(
  assignmentId: number,
  patch: { status?: string; notes?: string },
): Promise<Lead> {
  const data = await apiFetch<unknown>(`/leads/${assignmentId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  return LeadSchema.parse(data);
}

// ─── Export ───

export const ExportStatusSchema = z.object({
  doc_url: z.string().nullable(),
  sheet_url: z.string().nullable(),
  drive_folder_url: z.string().nullable(),
  google_auth_ok: z.boolean(),
});

export const ExportResultSchema = z.object({
  doc_url: z.string().nullable(),
  doc_appended: z.number(),
  sheet_url: z.string().nullable(),
  sheet_upserted: z.number(),
  sheet_mirrored: z.number(),
  exported_at: z.string(),
});

export type ExportStatus = z.infer<typeof ExportStatusSchema>;
export type ExportResult = z.infer<typeof ExportResultSchema>;

export async function getExportStatus(): Promise<ExportStatus> {
  const data = await apiFetch<unknown>("/export/status");
  return ExportStatusSchema.parse(data);
}

export async function triggerExport(): Promise<ExportResult> {
  const data = await apiFetch<unknown>("/export/now", { method: "POST" });
  return ExportResultSchema.parse(data);
}
