import { getLeads } from "@/lib/api";
import LeadTable from "@/components/LeadTable";

export const dynamic = "force-dynamic";

export default async function LeadsPage() {
  const data = await getLeads({ limit: 100 });

  return (
    <main className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-semibold mb-6">Leads</h1>
      {data.total === 0 ? (
        <p className="text-muted-foreground text-sm">
          No leads yet — run a sync and posts tagged &ldquo;lead&rdquo; will appear here.
        </p>
      ) : (
        <LeadTable leads={data.leads} total={data.total} />
      )}
    </main>
  );
}
