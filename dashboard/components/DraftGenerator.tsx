"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Item, GeneratedVariant } from "@/lib/api";
import { generateDraftsAction, saveDraftAction } from "@/app/actions";

function ItemRow({
  item,
  selected,
  onToggle,
}: {
  item: Item;
  selected: boolean;
  onToggle: () => void;
}) {
  const source = item.subreddit ? `r/${item.subreddit}` : item.source.toUpperCase();
  return (
    <label className="flex items-start gap-3 p-3 rounded-lg border cursor-pointer hover:bg-accent/50 transition-colors">
      <input
        type="checkbox"
        checked={selected}
        onChange={onToggle}
        className="mt-0.5 shrink-0"
      />
      <div className="min-w-0">
        <div className="text-xs text-muted-foreground mb-0.5">{source}</div>
        <p className="text-sm font-medium leading-snug line-clamp-2">{item.title}</p>
      </div>
    </label>
  );
}

export default function DraftGenerator({ items }: { items: Item[] }) {
  const router = useRouter();
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [notes, setNotes] = useState("");
  const [generating, setGenerating] = useState(false);
  const [variants, setVariants] = useState<GeneratedVariant[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function toggleItem(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleGenerate() {
    if (selectedIds.size === 0) return;
    setGenerating(true);
    setError("");
    setVariants([]);
    try {
      const res = await generateDraftsAction([...selectedIds], notes);
      setVariants(res.variants);
      setActiveTab(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  async function handleSave() {
    if (variants.length === 0) return;
    const chosen = variants[activeTab];
    setSaving(true);
    setError("");
    try {
      await saveDraftAction({
        item_ids: [...selectedIds],
        body: chosen.body,
        variant_index: chosen.variant_index,
      });
      router.push("/drafts");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Item picker */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold">
            Pick source items ({selectedIds.size} selected)
          </h2>
          {selectedIds.size > 0 && (
            <button
              onClick={() => setSelectedIds(new Set())}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Clear
            </button>
          )}
        </div>
        <div className="grid gap-2 max-h-80 overflow-y-auto pr-1">
          {items.map((item) => (
            <ItemRow
              key={item.id}
              item={item}
              selected={selectedIds.has(item.id)}
              onToggle={() => toggleItem(item.id)}
            />
          ))}
        </div>
      </section>

      {/* Notes */}
      <section>
        <label className="block text-sm font-semibold mb-2">
          Optional instructions
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="e.g. focus on the pain point angle, mention our n8n experience…"
          rows={2}
          className="w-full text-sm border rounded p-2 resize-none bg-background"
        />
      </section>

      {/* Generate button */}
      <button
        onClick={handleGenerate}
        disabled={selectedIds.size === 0 || generating}
        className="w-full bg-foreground text-background text-sm font-medium py-2.5 rounded-md hover:opacity-80 disabled:opacity-40 transition-opacity"
      >
        {generating ? "Generating 3 variants…" : "Generate drafts"}
      </button>

      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}

      {/* Variant tabs */}
      {variants.length > 0 && (
        <section className="space-y-3">
          <div className="flex gap-1 border-b">
            {variants.map((v, i) => (
              <button
                key={v.variant_index}
                onClick={() => setActiveTab(i)}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  activeTab === i
                    ? "border-foreground text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                Variant {v.variant_index + 1}
              </button>
            ))}
          </div>

          <div className="border rounded-lg p-4 bg-accent/20">
            <p className="text-sm whitespace-pre-wrap leading-relaxed">
              {variants[activeTab]?.body}
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="bg-foreground text-background text-sm font-medium px-4 py-2 rounded-md hover:opacity-80 disabled:opacity-40 transition-opacity"
            >
              {saving ? "Saving…" : `Save variant ${activeTab + 1}`}
            </button>
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="text-sm font-medium px-4 py-2 rounded-md border hover:bg-accent transition-colors disabled:opacity-40"
            >
              Regenerate
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
