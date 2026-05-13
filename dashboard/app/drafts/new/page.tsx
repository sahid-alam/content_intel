import { getFeed } from "@/lib/api";
import DraftGenerator from "@/components/DraftGenerator";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function NewDraftPage() {
  // Load non-noise items for the picker (latest 100)
  const feed = await getFeed({ limit: 100 });
  const items = feed.items.filter((item) => item.tag && item.tag !== "noise");

  return (
    <main className="p-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/drafts" className="text-muted-foreground hover:text-foreground text-sm">
          ← Drafts
        </Link>
        <h1 className="text-2xl font-semibold">New draft</h1>
      </div>

      {items.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No classified items yet. Run a sync first.
        </p>
      ) : (
        <DraftGenerator items={items} />
      )}
    </main>
  );
}
