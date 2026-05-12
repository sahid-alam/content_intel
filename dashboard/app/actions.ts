"use server";

import { triggerSync } from "@/lib/api";
import { revalidatePath } from "next/cache";

export async function syncNow() {
  const results = await triggerSync();
  revalidatePath("/");
  return results;
}
