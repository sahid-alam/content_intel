import { getDrafts } from "@/lib/api";
import DraftList from "@/components/DraftList";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function DraftsPage() {
  const data = await getDrafts({ limit: 50 });

  return (
    <main className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Drafts</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {data.total} saved draft{data.total !== 1 ? "s" : ""}
          </p>
        </div>
        <Link
          href="/drafts/new"
          className="bg-foreground text-background text-sm font-medium px-4 py-2 rounded-md hover:opacity-80 transition-opacity"
        >
          New draft
        </Link>
      </div>

      {data.drafts.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <p className="text-lg">No drafts yet</p>
          <p className="text-sm mt-2">Pick some feed items and generate your first LinkedIn post.</p>
        </div>
      ) : (
        <DraftList drafts={data.drafts} />
      )}
    </main>
  );
}
