"use client";

import { useState, useTransition } from "react";
import { updateAssignment } from "@/app/actions";
import type { Lead } from "@/lib/api";

const STATUS_OPTIONS = ["new", "reviewing", "contacted", "closed"] as const;

const STATUS_COLORS: Record<string, string> = {
  new: "bg-blue-100 text-blue-700",
  reviewing: "bg-yellow-100 text-yellow-700",
  contacted: "bg-green-100 text-green-700",
  closed: "bg-gray-100 text-gray-500",
};

const SIGNAL_COLORS: Record<string, string> = {
  none: "text-gray-400",
  mentioned: "text-yellow-600",
  explicit: "text-green-600 font-semibold",
};

export default function LeadTable({
  leads,
  total,
}: {
  leads: Lead[];
  total: number;
}) {
  return (
    <div>
      <p className="text-sm text-muted-foreground mb-4">
        {total} lead{total !== 1 ? "s" : ""}
      </p>
      <div className="rounded-lg border overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Post</th>
              <th className="px-4 py-3">Wants</th>
              <th className="px-4 py-3">Budget</th>
              <th className="px-4 py-3">Urgency</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 min-w-[160px]">Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {leads.map((lead) => (
              <LeadRow key={lead.assignment_id} lead={lead} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function LeadRow({ lead }: { lead: Lead }) {
  const [status, setStatus] = useState<string>(lead.status);
  const [notes, setNotes] = useState(lead.notes);
  const [isPending, startTransition] = useTransition();

  function handleStatusChange(next: string) {
    setStatus(next);
    startTransition(async () => {
      await updateAssignment(lead.assignment_id, { status: next });
    });
  }

  function handleNotesBlur() {
    if (notes === lead.notes) return;
    startTransition(async () => {
      await updateAssignment(lead.assignment_id, { notes });
    });
  }

  const sourceLabel = lead.subreddit
    ? `r/${lead.subreddit}`
    : lead.source.toUpperCase();

  return (
    <tr
      className={`hover:bg-muted/20 transition-colors ${isPending ? "opacity-50" : ""}`}
    >
      <td className="px-4 py-3">
        <span className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-blue-50 text-blue-700 font-bold text-sm">
          {lead.score.toFixed(1)}
        </span>
      </td>

      <td className="px-4 py-3 max-w-xs">
        <a
          href={lead.url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium hover:underline line-clamp-2 leading-snug"
        >
          {lead.title}
        </a>
        <p className="text-xs text-muted-foreground mt-0.5">
          {sourceLabel} · {lead.author}
        </p>
      </td>

      <td className="px-4 py-3 max-w-sm text-muted-foreground text-xs leading-relaxed">
        {lead.what_they_want}
      </td>

      <td className="px-4 py-3">
        <span className={`text-xs ${SIGNAL_COLORS[lead.budget_signal]}`}>
          {lead.budget_signal}
        </span>
      </td>

      <td className="px-4 py-3">
        <span className={`text-xs ${SIGNAL_COLORS[lead.urgency_signal]}`}>
          {lead.urgency_signal}
        </span>
      </td>

      <td className="px-4 py-3">
        <select
          value={status}
          onChange={(e) => handleStatusChange(e.target.value)}
          className={`rounded px-2 py-1 text-xs font-medium cursor-pointer border-0 focus:ring-1 focus:ring-ring focus:outline-none ${STATUS_COLORS[status] ?? "bg-gray-100"}`}
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </td>

      <td className="px-4 py-3">
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          onBlur={handleNotesBlur}
          placeholder="Add notes…"
          className="w-full bg-transparent text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring rounded px-1 py-0.5"
        />
      </td>
    </tr>
  );
}
