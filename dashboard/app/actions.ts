"use server";

import { revalidatePath } from "next/cache";
import { patchAssignment, triggerSync } from "@/lib/api";

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
