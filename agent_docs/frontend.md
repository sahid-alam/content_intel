# Dashboard (Next.js)

## Stack
- **Next.js 15+** App Router, TypeScript, React 19
- **Tailwind CSS** + **shadcn/ui** primitives (copied in, not a runtime dep)
- **pnpm** for package management (faster than npm, deterministic)
- **Zod** for runtime validation at API boundaries
- **No TanStack Query** — Server Components handle data fetching natively. Use TanStack Query only for client-side polling on the Feed (so "Sync now" status updates without page reload).

## Routes (App Router)

```
dashboard/app/
├── layout.tsx                    # root layout with nav
├── page.tsx                      # Feed (/)
├── leads/
│   ├── page.tsx                  # Leads table
│   └── [id]/page.tsx             # Single lead detail (optional)
├── drafts/
│   ├── page.tsx                  # Saved drafts list
│   └── new/page.tsx              # Compose: pick items → generate
├── settings/page.tsx             # subs, caps, voice profile, Drive URLs
└── api/                          # only used if a Server Action needs HTTP
    └── (mostly empty in v1)
```

## Data flow (v1)

Server Components fetch from FastAPI directly:

```tsx
// app/page.tsx (Feed)
import { getFeed } from "@/lib/api";

export default async function FeedPage({ searchParams }: { searchParams: { tag?: string } }) {
  const items = await getFeed({ tag: searchParams.tag });
  return <FeedList items={items} />;
}
```

`lib/api.ts` is a single typed client with one fetch wrapper that prefixes `process.env.BACKEND_URL` (= `http://localhost:8000` in dev). Throws typed errors on non-2xx. No axios.

Mutations go through Server Actions:

```tsx
// app/leads/actions.ts
"use server";
import { updateLeadStatus as apiUpdate } from "@/lib/api";
import { revalidatePath } from "next/cache";

export async function updateLeadStatus(leadId: number, status: string) {
  await apiUpdate(leadId, { status });
  revalidatePath("/leads");
}
```

## Data flow (v2 — after Supabase migration)

`lib/api.ts` swaps from "call FastAPI" to "call Supabase client." Components don't change. Server Actions don't change shape, only their implementation.

See `deployment.md` for the migration details.

## Pages

### Feed (`/`)
- Top bar: "Sync now" button (Server Action → POST /sync), last-sync timestamp, today's AI usage pill
- Left rail: filters via URL search params (`?source=reddit&tag=lead&since=24h`). URL-driven so filters are shareable / bookmarkable.
- Card list. Each card:
  - Title (prominent), one-liner summary (secondary)
  - Source badge + tag pill (color-coded)
  - Score, comments, age (small, right)
  - Hover actions: "Open source", "Use in draft" (multi-select via client component), "Draft now" (→ /drafts/new with this item pre-selected)
- Header buttons: "Export to Drive now"; opens Doc/Sheet URLs after success

### Leads (`/leads`)
- Table with columns: created, source, asker, what_they_want, urgency, score, status, notes, actions
- `status` (dropdown) and `notes` (inline edit) — these are the human-owned columns; syncs to the Sheet on next export
- Default filter: `status = new`; sort: `score DESC, created_at DESC`
- "Open in Sheet" button → opens the live Drive Sheet
- Bulk select → "Export selected as CSV"

### Drafts compose (`/drafts/new`)
- Step 1: pick 1-3 items from feed (or arrive pre-selected via query string)
- Step 2: click "Generate" → Server Action → loading state showing model name
- Step 3: 3 tabs labeled "Variant A / B / C", each editable in a textarea
- Step 4: "Save this one" + "Copy" + "Regenerate all" + "Discard"

### Saved drafts (`/drafts`)
- Card grid. Each: title (first 60 chars), source items as badges, model, age, "Copy" / "Mark as published"
- "Mark as published" is purely informational — no LinkedIn API

### Settings (`/settings`)
- Subreddit list editor (textarea, comma-separated)
- HN keyword list editor
- Lookback hours
- Daily caps (Flash + Gemma) with current usage
- Voice profile editor — textarea editing `voice_profile.md`. Warning text: "this file is also referenced by your Cowork Project — keep them in sync"
- Drive integration block: Doc URL (read-only, click to open), Sheet URL, "Re-run export now" button

## User identity (v1 → v2)

v1: hardcoded. `lib/user.ts`:
```ts
export async function getCurrentUser() {
  return { id: "self", name: "Me" };
}
```

Every Server Component and Server Action calls `getCurrentUser()` and passes the id to API calls. This looks redundant in v1 (single user) but it's the **single most important habit** for the v2 migration. Don't shortcut it.

v2: same function reads the Supabase Auth session. Components don't change.

## Visual design

- Information-dense (Linear/Stripe-dashboard feel)
- Sans-serif throughout; weight contrast does the work
- Color used sparingly — tag pills the only saturated color
- Muted tag colors: dusty rose `pain`, warm amber `lead`, slate blue `trend`, sage `signal`, gray `noise`
- Generous whitespace inside cards, tight rhythm between
- No dark mode in v1

## Don't build
- Auth UI in v1 (single user; v2 uses Supabase Auth hosted UI)
- Drag-and-drop kanban for leads (dropdown is fine)
- Real-time websockets (poll on focus)
- Rich text editor (textarea is fine; you edit in LinkedIn anyway)
- LinkedIn API integration

## Performance discipline

- **Server Components by default; `'use client'` only when interactivity demands it** (filters, multi-select, inline edits, modal state).
- **Stream loading states** with `loading.tsx` at the route level. Feed shouldn't block on classifier load.
- **Revalidate, don't refetch.** After a mutation, `revalidatePath("/leads")` — let Next.js refetch on next render.