"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PortfolioItem, PortfolioPnLResponse, PortfolioItemWithPnL } from "@/lib/types";
import { Plus, Trash2, TrendingUp, TrendingDown, RefreshCw, Wifi, WifiOff, IndianRupee, Wallet } from "lucide-react";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function pnlColor(value: number | null): string {
  if (value === null) return "text-zinc-400";
  return value >= 0 ? "text-emerald-400" : "text-red-400";
}

function pnlBg(value: number | null): string {
  if (value === null) return "";
  return value >= 0 ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400";
}

function fmtINR(v: number | null | undefined): string {
  if (v == null) return "—";
  return "₹" + Math.abs(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return (v >= 0 ? "+" : "") + v.toFixed(2) + "%";
}

// ─── Summary Card ──────────────────────────────────────────────────────────────

function SummaryCard({
  label,
  value,
  sub,
  colorClass = "text-zinc-100",
  icon,
}: {
  label: string;
  value: string;
  sub?: string;
  colorClass?: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 flex flex-col gap-2 hover:border-zinc-700 transition-colors">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">{label}</span>
        {icon && <span className="text-zinc-600">{icon}</span>}
      </div>
      <span className={`text-2xl font-bold tracking-tight ${colorClass}`}>{value}</span>
      {sub && <span className="text-xs text-zinc-500">{sub}</span>}
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

export default function PortfolioPage() {
  const [pnlData, setPnlData] = useState<PortfolioPnLResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Add form state
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [frequency, setFrequency] = useState("Long-term");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    fetchPnl();
  }, []);

  const fetchPnl = async () => {
    setSyncing(true);
    setError(null);
    try {
      const data = await api.user.getPortfolioPnl();
      setPnlData(data);
    } catch (err) {
      setError("Failed to load portfolio. Check backend connection.");
      console.error(err);
    } finally {
      setLoading(false);
      setSyncing(false);
    }
  };

  const addItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol || !quantity || !price) return;
    setAdding(true);
    try {
      await api.user.upsertPortfolioItem({
        symbol: symbol.toUpperCase(),
        quantity: parseFloat(quantity),
        average_buy_price: parseFloat(price),
        strategy_frequency: frequency,
      });
      setSymbol(""); setQuantity(""); setPrice("");
      await fetchPnl();
    } catch (err) {
      console.error(err);
    } finally {
      setAdding(false);
    }
  };

  const deleteItem = async (sym: string) => {
    // For live-synced items we can't delete from Groww — just refetch
    // For local items, find by symbol and delete
    const items = await api.user.getPortfolio();
    const local = items.find((i) => i.symbol === sym && !i.is_live_synced);
    if (local?.id) {
      await api.user.deletePortfolioItem(local.id);
      await fetchPnl();
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-zinc-500 text-sm">Syncing with Groww…</p>
        </div>
      </div>
    );
  }

  const summary = pnlData?.summary;
  const holdings: PortfolioItemWithPnL[] = pnlData?.holdings ?? [];
  const isLive = pnlData?.source === "live_groww_api";

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">

      {/* ── Header ── */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
          <p className="text-zinc-500 mt-1 text-sm">
            {isLive
              ? "Live sync from Groww · prices from local DB"
              : "Local holdings · prices from local DB"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Live sync badge */}
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${
            isLive
              ? "border-emerald-800 bg-emerald-950 text-emerald-400"
              : "border-zinc-700 bg-zinc-900 text-zinc-400"
          }`}>
            {isLive ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
            {isLive ? "Groww Live" : "Local DB"}
          </span>
          <button
            onClick={fetchPnl}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-zinc-700 text-sm text-zinc-300 hover:border-zinc-500 hover:text-zinc-100 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-900 bg-red-950/40 px-5 py-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* ── Summary Cards ── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          label="Total Invested"
          value={fmtINR(summary?.total_invested)}
          sub={`${summary?.holding_count ?? 0} holdings`}
          icon={<IndianRupee className="h-4 w-4" />}
        />
        <SummaryCard
          label="Current Value"
          value={summary?.total_current_value != null ? fmtINR(summary.total_current_value) : "—"}
          sub={summary?.total_current_value == null ? "No price data in DB" : "Mark-to-market"}
          colorClass={summary?.total_current_value != null ? "text-zinc-100" : "text-zinc-500"}
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <SummaryCard
          label="Unrealized P&L"
          value={summary?.total_unrealized_pnl != null
            ? (summary.total_unrealized_pnl >= 0 ? "+" : "") + fmtINR(summary.total_unrealized_pnl)
            : "—"}
          sub={summary?.total_pnl_pct != null ? fmtPct(summary.total_pnl_pct) + " overall" : undefined}
          colorClass={summary?.total_unrealized_pnl != null
            ? summary.total_unrealized_pnl >= 0 ? "text-emerald-400" : "text-red-400"
            : "text-zinc-500"}
          icon={summary?.total_unrealized_pnl != null && summary.total_unrealized_pnl >= 0
            ? <TrendingUp className="h-4 w-4" />
            : <TrendingDown className="h-4 w-4" />}
        />
        <SummaryCard
          label="Available Cash"
          value={pnlData?.available_cash != null ? fmtINR(pnlData.available_cash) : "—"}
          sub={pnlData?.available_cash != null ? "CNC balance (Groww)" : "Connect Groww for live cash"}
          colorClass="text-blue-400"
          icon={<Wallet className="h-4 w-4" />}
        />
      </div>

      {/* ── Holdings Table + Add Form ── */}
      <div className="grid gap-8 lg:grid-cols-[1fr_300px]">

        {/* Table */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-zinc-800/60 text-zinc-500 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 font-medium">Stock</th>
                <th className="px-4 py-3 font-medium text-right">Qty</th>
                <th className="px-4 py-3 font-medium text-right">Avg Cost</th>
                <th className="px-4 py-3 font-medium text-right">LTP</th>
                <th className="px-4 py-3 font-medium text-right">Invested</th>
                <th className="px-4 py-3 font-medium text-right">Current</th>
                <th className="px-4 py-3 font-medium text-right">P&amp;L</th>
                <th className="px-4 py-3 font-medium text-right">30d</th>
                <th className="px-4 py-3 font-medium">Strategy</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {holdings.length === 0 && (
                <tr>
                  <td colSpan={10} className="px-4 py-12 text-center text-zinc-600">
                    No holdings yet. Add one below or connect your Groww account.
                  </td>
                </tr>
              )}
              {holdings.map((item) => (
                <tr key={item.symbol} className="hover:bg-zinc-800/20 transition-colors group">
                  {/* Stock */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div>
                        <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
                          {item.symbol}
                          {item.is_live_synced && (
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" title="Live synced" />
                          )}
                        </div>
                        <div className="text-xs text-zinc-500 truncate max-w-[140px]">{item.company_name}</div>
                      </div>
                    </div>
                  </td>
                  {/* Qty */}
                  <td className="px-4 py-3 text-right text-zinc-300">{item.quantity}</td>
                  {/* Avg Cost */}
                  <td className="px-4 py-3 text-right text-zinc-300">{fmtINR(item.average_buy_price)}</td>
                  {/* LTP */}
                  <td className="px-4 py-3 text-right">
                    {item.latest_price != null ? (
                      <div>
                        <div className="text-zinc-100">{fmtINR(item.latest_price)}</div>
                        {item.price_date && (
                          <div className="text-[10px] text-zinc-600">{item.price_date}</div>
                        )}
                      </div>
                    ) : (
                      <span className="text-zinc-600 text-xs">No data</span>
                    )}
                  </td>
                  {/* Invested */}
                  <td className="px-4 py-3 text-right text-zinc-400">{fmtINR(item.invested_value)}</td>
                  {/* Current */}
                  <td className="px-4 py-3 text-right">
                    {item.current_value != null
                      ? <span className="text-zinc-100 font-medium">{fmtINR(item.current_value)}</span>
                      : <span className="text-zinc-600">—</span>}
                  </td>
                  {/* P&L */}
                  <td className="px-4 py-3 text-right">
                    {item.unrealized_pnl != null ? (
                      <div className={pnlColor(item.unrealized_pnl)}>
                        <div className="font-medium">
                          {item.unrealized_pnl >= 0 ? "+" : ""}{fmtINR(item.unrealized_pnl)}
                        </div>
                        <div className={`text-[11px] px-1.5 py-0.5 rounded-full inline-block mt-0.5 ${pnlBg(item.pnl_pct)}`}>
                          {fmtPct(item.pnl_pct)}
                        </div>
                      </div>
                    ) : (
                      <span className="text-zinc-600">—</span>
                    )}
                  </td>
                  {/* 30d */}
                  <td className="px-4 py-3 text-right">
                    {item.change_30d_pct != null ? (
                      <span className={`text-xs font-medium ${pnlColor(item.change_30d_pct)}`}>
                        {fmtPct(item.change_30d_pct)}
                      </span>
                    ) : <span className="text-zinc-600">—</span>}
                  </td>
                  {/* Strategy */}
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center rounded-full bg-zinc-800 px-2 py-1 text-[11px] font-medium text-zinc-400">
                      {item.strategy_frequency}
                    </span>
                  </td>
                  {/* Delete */}
                  <td className="px-4 py-3 text-right">
                    {!item.is_live_synced && (
                      <button
                        onClick={() => deleteItem(item.symbol)}
                        className="text-zinc-700 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Add Form */}
        <div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 sticky top-6">
            <h2 className="font-semibold text-zinc-100 mb-5 flex items-center gap-2 text-sm">
              <Plus className="h-4 w-4 text-emerald-500" />
              Add Manual Holding
            </h2>
            <form onSubmit={addItem} className="space-y-4">
              {[
                { label: "Symbol", placeholder: "e.g. RELIANCE", value: symbol, set: setSymbol, type: "text" },
                { label: "Quantity", placeholder: "e.g. 100", value: quantity, set: setQuantity, type: "number" },
                { label: "Avg Buy Price (₹)", placeholder: "e.g. 2500", value: price, set: setPrice, type: "number" },
              ].map(({ label, placeholder, value, set, type }) => (
                <div key={label} className="space-y-1.5">
                  <label className="text-xs text-zinc-500 font-medium">{label}</label>
                  <input
                    type={type}
                    step="any"
                    required
                    placeholder={placeholder}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-700 focus:outline-none focus:border-emerald-600 transition-colors"
                    value={value}
                    onChange={(e) => set(e.target.value)}
                  />
                </div>
              ))}
              <div className="space-y-1.5">
                <label className="text-xs text-zinc-500 font-medium">Strategy</label>
                <select
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-emerald-600 transition-colors"
                  value={frequency}
                  onChange={(e) => setFrequency(e.target.value)}
                >
                  {["Daily", "Weekly", "Monthly", "Yearly", "Long-term"].map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>
              <button
                type="submit"
                disabled={adding}
                className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-medium text-sm py-2.5 rounded-lg transition-colors mt-1"
              >
                {adding ? "Adding…" : "Add to Portfolio"}
              </button>
            </form>

            {/* Account info (if Groww live) */}
            {pnlData?.account_info?.ucc && (
              <div className="mt-6 pt-5 border-t border-zinc-800 space-y-2">
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Groww Account</p>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-zinc-500">UCC</span>
                    <span className="text-zinc-300 font-mono">{pnlData.account_info.ucc}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-zinc-500">Segments</span>
                    <span className="text-zinc-300">{pnlData.account_info.active_segments.join(", ") || "—"}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-zinc-500">DDPI</span>
                    <span className={pnlData.account_info.ddpi_enabled ? "text-emerald-400" : "text-zinc-500"}>
                      {pnlData.account_info.ddpi_enabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
