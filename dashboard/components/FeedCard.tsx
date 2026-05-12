import type { Item } from "@/lib/api";

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3_600_000);
  if (h < 1) return "just now";
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

const SOURCE_LABELS: Record<string, string> = { hn: "HN", reddit: "Reddit" };

const TAG_STYLES: Record<string, string> = {
  lead:   "bg-amber-100 text-amber-800",
  pain:   "bg-rose-100 text-rose-800",
  trend:  "bg-blue-100 text-blue-800",
  signal: "bg-emerald-100 text-emerald-800",
  noise:  "bg-zinc-100 text-zinc-400",
};

export function FeedCard({ item }: { item: Item & { tag?: string } }) {
  const sourceLabel = SOURCE_LABELS[item.source] ?? item.source.toUpperCase();
  const sub = item.subreddit ? ` r/${item.subreddit}` : "";
  const isNoise = item.tag === "noise";

  return (
    <article
      className={`rounded-lg border p-4 transition-colors ${
        isNoise
          ? "border-zinc-100 bg-zinc-50 opacity-60"
          : "border-zinc-200 bg-white hover:border-zinc-300"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium text-zinc-900 hover:underline leading-snug"
        >
          {item.title}
        </a>
        <div className="flex shrink-0 items-center gap-1.5">
          {item.tag && (
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TAG_STYLES[item.tag] ?? TAG_STYLES.noise}`}>
              {item.tag}
            </span>
          )}
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500 font-mono">
            {sourceLabel}{sub}
          </span>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-3 text-xs text-zinc-400">
        <span>↑ {item.score}</span>
        <span>{item.num_comments} comments</span>
        <span>{timeAgo(item.created_utc)}</span>
        {item.author && <span>by {item.author}</span>}
      </div>
    </article>
  );
}
