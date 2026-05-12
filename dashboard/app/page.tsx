import Link from "next/link";
import { getFeed, getTodayUsage } from "@/lib/api";
import { FeedCard } from "@/components/FeedCard";
import { SyncButton } from "@/components/SyncButton";

const SOURCES = [
  { label: "All", value: undefined },
  { label: "HN", value: "hn" },
  { label: "Reddit", value: "reddit" },
];

const TAGS = [
  { label: "All tags", value: undefined },
  { label: "lead", value: "lead" },
  { label: "pain", value: "pain" },
  { label: "trend", value: "trend" },
  { label: "signal", value: "signal" },
  { label: "noise", value: "noise" },
];

export default async function FeedPage({
  searchParams,
}: {
  searchParams: Promise<{ source?: string; tag?: string }>;
}) {
  const { source, tag } = await searchParams;

  const [feed, usage] = await Promise.allSettled([
    getFeed({ source, tag, limit: 50 }),
    getTodayUsage(),
  ]);

  const feedData = feed.status === "fulfilled" ? feed.value : null;
  const callsToday = usage.status === "fulfilled" ? usage.value.calls_today : null;

  function filterLink(params: { source?: string; tag?: string }) {
    const qs = new URLSearchParams();
    if (params.source) qs.set("source", params.source);
    if (params.tag) qs.set("tag", params.tag);
    return `/${qs.toString() ? `?${qs}` : ""}`;
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900">Feed</h1>
          {feedData && (
            <p className="text-sm text-zinc-400 mt-0.5">
              {feedData.total} items
              {callsToday != null && (
                <span className="ml-3 rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500">
                  {callsToday} AI calls today
                </span>
              )}
            </p>
          )}
        </div>
        <SyncButton />
      </div>

      {/* Source filter */}
      <div className="mb-3 flex gap-2">
        {SOURCES.map(({ label, value }) => {
          const active = (source ?? undefined) === value;
          return (
            <Link
              key={label}
              href={filterLink({ source: value, tag })}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                active ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
              }`}
            >
              {label}
            </Link>
          );
        })}
      </div>

      {/* Tag filter */}
      <div className="mb-6 flex flex-wrap gap-2">
        {TAGS.map(({ label, value }) => {
          const active = (tag ?? undefined) === value;
          return (
            <Link
              key={label}
              href={filterLink({ source, tag: value })}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                active ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
              }`}
            >
              {label}
            </Link>
          );
        })}
      </div>

      {!feedData && (
        <p className="text-sm text-red-500">Backend unreachable — is it running?</p>
      )}
      {feedData && feedData.items.length === 0 && (
        <p className="text-sm text-zinc-400">No items yet — click Sync now.</p>
      )}
      {feedData && (
        <ul className="flex flex-col gap-3">
          {feedData.items.map((item) => (
            <li key={item.id}>
              <FeedCard item={item} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
