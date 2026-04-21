import { api } from "@/lib/api";
import { MarketPulseCard } from "@/components/discovery/market-pulse";
import { SectorGrid } from "@/components/discovery/sector-grid";
import { BucketCarousel } from "@/components/discovery/bucket-carousel";
import { MoversTable } from "@/components/discovery/movers-table";

export const dynamic = "force-dynamic";
export const revalidate = 300; // Revalidate every 5 minutes

async function getDiscoveryData() {
  try {
    const [marketPulse, sectors, buckets, movers, plans] = await Promise.all([
      api.discovery.getMarketPulse(),
      api.discovery.getSectors(),
      api.discovery.getBuckets(6),
      api.discovery.getMovers(10),
      api.user.getPlans().catch(() => []), // gracefully handle if user API fails
    ]);

    return { marketPulse, sectors, buckets, movers, plans, error: null };
  } catch (error) {
    console.error("Failed to fetch discovery data:", error);
    return {
      marketPulse: null,
      sectors: null,
      buckets: null,
      movers: null,
      plans: [],
      error: "Failed to load data. Make sure the API server is running.",
    };
  }
}

export default async function DiscoveryPage() {
  const { marketPulse, sectors, buckets, movers, plans, error } = await getDiscoveryData();

  if (error) {
    return (
      <div className="p-8">
        <div className="rounded-lg bg-red-900/20 border border-red-800 p-6 text-center">
          <h2 className="text-xl font-semibold text-red-400">Connection Error</h2>
          <p className="mt-2 text-zinc-400">{error}</p>
          <p className="mt-4 text-sm text-zinc-500">
            Start the API server with: <code className="bg-zinc-800 px-2 py-1 rounded">uv run python main.py serve</code>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Discovery</h1>
        <p className="text-zinc-400 mt-1">Explore trending assets tailored for your strategies</p>
      </div>

      {plans && plans.length > 0 && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 flex gap-4 items-center overflow-x-auto">
          <span className="text-sm font-semibold text-emerald-400 whitespace-nowrap">Active Plans:</span>
          {plans.map(plan => (
            <div key={plan.id} className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-1.5 text-sm whitespace-nowrap">
              <span className="text-zinc-300">{plan.frequency}: </span>
              <span className="font-medium text-emerald-400">₹{plan.allocated_amount}</span>
            </div>
          ))}
        </div>
      )}

      {/* Market Pulse & Sectors */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          {marketPulse && <MarketPulseCard data={marketPulse} />}
        </div>
        <div className="lg:col-span-2">
          {sectors && <SectorGrid sectors={sectors} />}
        </div>
      </div>

      {/* Buckets */}
      <div className="space-y-8">
        {buckets?.slice(0, 4).map((bucket) => (
          <BucketCarousel key={bucket.bucket_id} bucket={bucket} />
        ))}
      </div>

      {/* Movers Table */}
      {movers && <MoversTable data={movers} />}

      {/* More Buckets */}
      <div className="space-y-8">
        {buckets?.slice(4).map((bucket) => (
          <BucketCarousel key={bucket.bucket_id} bucket={bucket} />
        ))}
      </div>
    </div>
  );
}
