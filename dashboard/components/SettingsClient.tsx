"use client";

import { exportNow } from "@/app/actions";
import type { ExportStatus } from "@/lib/api";
import { useTransition } from "react";

interface Props {
  status: ExportStatus | null;
}

export default function SettingsClient({ status }: Props) {
  const [isPending, startTransition] = useTransition();

  function handleExport() {
    startTransition(async () => {
      await exportNow();
    });
  }

  return (
    <div className="space-y-6">
      {/* Google Drive auth status */}
      <section className="border rounded-lg p-4 space-y-3">
        <h2 className="font-medium">Google Drive</h2>
        {status === null ? (
          <p className="text-sm text-muted-foreground">Backend unavailable</p>
        ) : (
          <>
            <div className="flex items-center gap-2 text-sm">
              <span
                className={`inline-block w-2 h-2 rounded-full ${
                  status.google_auth_ok ? "bg-green-500" : "bg-red-500"
                }`}
              />
              {status.google_auth_ok ? (
                <span>Authenticated</span>
              ) : (
                <span className="text-red-600">
                  Not authenticated — run{" "}
                  <code className="bg-muted px-1 rounded text-xs">
                    uv run python scripts/google_auth.py
                  </code>{" "}
                  in <code className="bg-muted px-1 rounded text-xs">backend/</code>
                </span>
              )}
            </div>

            <div className="text-sm space-y-1">
              {status.drive_folder_url && (
                <p>
                  <span className="text-muted-foreground">Drive folder: </span>
                  <a
                    href={status.drive_folder_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline break-all"
                  >
                    {status.drive_folder_url}
                  </a>
                </p>
              )}
              {status.sheet_url && (
                <p>
                  <span className="text-muted-foreground">Leads sheet: </span>
                  <a
                    href={status.sheet_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline break-all"
                  >
                    {status.sheet_url}
                  </a>
                </p>
              )}
            </div>
          </>
        )}
      </section>

      {/* Export */}
      <section className="border rounded-lg p-4 space-y-3">
        <h2 className="font-medium">Export</h2>
        <p className="text-sm text-muted-foreground">
          Writes non-noise items to the weekly Google Doc and upserts leads to
          the Sheet. Human edits in the Sheet (status, notes) are mirrored back
          to the database.
        </p>
        <button
          onClick={handleExport}
          disabled={isPending || !status?.google_auth_ok}
          className="px-4 py-2 text-sm font-medium bg-foreground text-background rounded-md
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPending ? "Exporting…" : "Export now"}
        </button>
      </section>
    </div>
  );
}
