"use server";

import { revalidatePath } from "next/cache";
import {
  deleteDraft,
  generateDrafts,
  patchAssignment,
  patchDraft,
  saveDraft,
  triggerExport,
  triggerSync,
  type GenerateResponse,
  type Draft,
} from "@/lib/api";

export async function syncNow() {
  const results = await triggerSync();
  revalidatePath("/");
  return results;
}

export async function updateAssignment(
  assignmentId: number,
  patch: { status?: string; notes?: string },
) {
  await patchAssignment(assignmentId, patch);
  revalidatePath("/leads");
}

export async function exportNow() {
  const result = await triggerExport();
  revalidatePath("/settings");
  return result;
}

export async function generateDraftsAction(
  itemIds: number[],
  notes: string,
): Promise<GenerateResponse> {
  return generateDrafts(itemIds, notes);
}

export async function saveDraftAction(payload: {
  item_ids: number[];
  body: string;
  variant_index: number;
}): Promise<Draft> {
  const draft = await saveDraft(payload);
  revalidatePath("/drafts");
  return draft;
}

export async function patchDraftAction(
  draftId: number,
  patch: { body?: string; published_at?: string | null },
): Promise<Draft> {
  const draft = await patchDraft(draftId, patch);
  revalidatePath("/drafts");
  return draft;
}

export async function deleteDraftAction(draftId: number): Promise<void> {
  await deleteDraft(draftId);
  revalidatePath("/drafts");
}
