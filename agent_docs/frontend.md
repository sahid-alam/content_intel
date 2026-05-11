# Frontend

## Stack
- **Vite + React 18 + TypeScript** — Vite is the default in 2026; CRA is dead.
- **TanStack Query (React Query)** for server state. Don't use Redux/Zustand for API data.
- **Tailwind CSS** for styling. Avoid component libraries with heavy theming you'll fight later.
- **shadcn/ui** for primitives — copy components into the repo so you own them; not a runtime dependency.
- **TanStack Router** or **React Router v6** — either is fine; pick one and don't mix.

## Routes
```
/                  → Feed
/leads             → Lead list
/drafts            → Saved drafts (LinkedIn posts + lead magnet outlines)
/drafts/new        → Compose: pick items → generate
/settings          → Subreddit/HN query config, model caps, voice profile editor
```

## Feed view
- Top bar: "Sync now" button (POST /sync), "last sync" timestamp, daily AI-spend pill
- Filters (left rail or top): source (reddit/HN), tag (pain/lead/trend/signal), subreddit, time window, min score
- List: cards showing title, one-liner summary, source badge, score, comment count, age, tag pill
- Each card has actions: "Open source" (external), "Use in draft" (multi-select), "Generate post from this" (single-shot Pro call), "View raw"

## Lead list
- Table-style. Columns: created (relative), source, asker, what_they_want, urgency, score, status, actions
- Inline edit on `notes` and `status`
- Bulk-select → "Export selected as CSV"
- Default sort: `score DESC, created_at DESC`

## Drafts compose
- Step 1: pick 1-3 items from feed (or a saved cluster)
- Step 2: choose kind (linkedin_post | lead_magnet_outline)
- Step 3: hit "Generate" → loading state with model name visible (so you know what you're paying for)
- Step 4: editable text area with the result; "Copy", "Save", "Regenerate", "Discard"

## State management rules
- Server state (items, leads, drafts) → TanStack Query, never local React state
- UI state (filters, selection, modal open) → React state in the relevant component
- Persistent UI state (default filters) → localStorage via a tiny custom hook
- **Don't** put server data in localStorage. The DB is the truth.

## API client
Single file `src/lib/api.ts`. One `fetch` wrapper that:
- Prefixes the backend base URL (`http://localhost:8000` in dev, env-driven in prod)
- Throws on non-2xx with a typed error
- JSON-encodes/decodes
- No axios — fetch is fine and one less dep

Then export typed functions: `getFeed(filters)`, `getLeads(...)`, `generateDraft({ kind, itemIds })`, etc. TanStack Query keys mirror these function names.

## Don't build
- Auth, multi-user accounts, sharing, role-based access. Single-user local tool.
- Dark mode toggle. Pick one theme (Tailwind `dark:` variant) and ship it. Add later if you actually want it.
- Drag-and-drop kanban for leads. Status is a dropdown. The fancy version is a v2 problem.
- Real-time updates / websockets. Polling on focus (TanStack Query default) is fine.