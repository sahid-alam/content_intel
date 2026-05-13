"use client";

import { useState } from "react";
import type { Draft } from "@/lib/api";
import { deleteDraftAction, patchDraftAction } from "@/app/actions";
import { useRouter } from "next/navigation";

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function DraftCard({ draft }: { draft: Draft }) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(draft.body);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      await patchDraftAction(draft.id, { body });
      setEditing(false);
      router.refresh();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this draft?")) return;
    setDeleting(true);
    try {
      await deleteDraftAction(draft.id);
      router.refresh();
    } finally {
      setDeleting(false);
    }
  }

  async function handleMarkPublished() {
    await patchDraftAction(draft.id, { published_at: new Date().toISOString() });
    router.refresh();
  }

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{formatDate(draft.created_at)}</span>
        <div className="flex items-center gap-3">
          {draft.published_at ? (
            <span className="text-green-600 dark:text-green-400">
              Published {formatDate(draft.published_at)}
            </span>
          ) : (
            <button
              onClick={handleMarkPublished}
              className="hover:text-foreground transition-colors"
            >
              Mark published
            </button>
          )}
          <button
            onClick={() => setEditing(!editing)}
            className="hover:text-foreground transition-colors"
          >
            {editing ? "Cancel" : "Edit"}
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="hover:text-red-500 transition-colors disabled:opacity-50"
          >
            {deleting ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>

      {editing ? (
        <div className="space-y-2">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={10}
            className="w-full text-sm border rounded p-2 font-mono resize-y bg-background"
          />
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-sm bg-foreground text-background px-3 py-1.5 rounded hover:opacity-80 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      ) : (
        <p className="text-sm whitespace-pre-wrap leading-relaxed">{body}</p>
      )}

      <div className="text-xs text-muted-foreground">
        {draft.item_ids.length} source{draft.item_ids.length !== 1 ? "s" : ""} · variant {draft.variant_index + 1} · {draft.model}
      </div>
    </div>
  );
}

export default function DraftList({ drafts }: { drafts: Draft[] }) {
  return (
    <div className="space-y-4">
      {drafts.map((d) => (
        <DraftCard key={d.id} draft={d} />
      ))}
    </div>
  );
}
