"use client";

import { useTransition } from "react";
import { syncNow } from "@/app/actions";

export function SyncButton() {
  const [pending, startTransition] = useTransition();

  function handleSync() {
    startTransition(async () => {
      const results = await syncNow();
      const total = results.reduce((s, r) => s + r.inserted, 0);
      alert(`Sync complete — ${total} new item${total !== 1 ? "s" : ""} inserted`);
    });
  }

  return (
    <button
      onClick={handleSync}
      disabled={pending}
      className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50 transition-colors"
    >
      {pending ? "Syncing…" : "Sync now"}
    </button>
  );
}
