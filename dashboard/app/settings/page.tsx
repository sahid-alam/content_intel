import { getExportStatus } from "@/lib/api";
import SettingsClient from "@/components/SettingsClient";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  let status = null;
  try {
    status = await getExportStatus();
  } catch {
    // backend not running
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      <h1 className="text-xl font-semibold">Settings</h1>
      <SettingsClient status={status} />
    </div>
  );
}
