"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PortfolioItem } from "@/lib/types";
import { formatINR, formatPercent } from "@/lib/utils"; // need to implement basic formatPercent if missing, but we have it in api.ts so we should use api.ts
import { Plus, Trash2 } from "lucide-react";

export default function PortfolioPage() {
  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [frequency, setFrequency] = useState("Long-term");

  useEffect(() => {
    fetchPortfolio();
  }, []);

  const fetchPortfolio = async () => {
    try {
      const data = await api.user.getPortfolio();
      setItems(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const addItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol || !quantity || !price) return;

    try {
      await api.user.upsertPortfolioItem({
        symbol: symbol.toUpperCase(),
        quantity: parseFloat(quantity),
        average_buy_price: parseFloat(price),
        strategy_frequency: frequency,
      });
      setSymbol("");
      setQuantity("");
      setPrice("");
      fetchPortfolio();
    } catch (err) {
      console.error(err);
    }
  };

  const deleteItem = async (id: number) => {
    try {
      await api.user.deletePortfolioItem(id);
      fetchPortfolio();
    } catch (err) {
      console.error(err);
    }
  };

  const totalValue = items.reduce((sum, item) => sum + (item.quantity * item.average_buy_price), 0);

  if (loading) return <div className="p-8">Loading...</div>;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Your Portfolio</h1>
        <p className="text-zinc-400 mt-2">Manage your manual holdings and track their strategies.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
          <div className="text-sm font-medium text-zinc-400">Total Invested Value</div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">₹{totalValue.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
          </div>
        </div>
      </div>

      <div className="grid gap-8 md:grid-cols-[1fr_300px]">
        <div className="space-y-6">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 overflow-hidden">
            <table className="w-full text-sm text-left">
              <thead className="bg-zinc-800/50 text-zinc-400">
                <tr>
                  <th className="px-4 py-3 font-medium">Symbol</th>
                  <th className="px-4 py-3 font-medium text-right">Quantity</th>
                  <th className="px-4 py-3 font-medium text-right">Avg Price</th>
                  <th className="px-4 py-3 font-medium text-right">Value</th>
                  <th className="px-4 py-3 font-medium">Strategy</th>
                  <th className="px-4 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-zinc-500">
                      No holdings added yet.
                    </td>
                  </tr>
                )}
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-zinc-800/20">
                    <td className="px-4 py-3 font-medium text-emerald-400">{item.symbol}</td>
                    <td className="px-4 py-3 text-right">{item.quantity}</td>
                    <td className="px-4 py-3 text-right">₹{item.average_buy_price.toLocaleString('en-IN')}</td>
                    <td className="px-4 py-3 text-right font-medium">₹{(item.quantity * item.average_buy_price).toLocaleString('en-IN')}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center rounded-full bg-zinc-800 px-2 py-1 text-xs font-medium text-zinc-300">
                        {item.strategy_frequency}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button 
                        onClick={() => item.id && deleteItem(item.id)}
                        className="text-zinc-500 hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 sticky top-6">
            <h2 className="font-medium text-zinc-100 mb-4 flex items-center gap-2">
              <Plus className="h-4 w-4 text-emerald-500" />
              Add Holding
            </h2>
            <form onSubmit={addItem} className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs text-zinc-400 font-medium">Symbol</label>
                <input 
                  type="text" 
                  required
                  placeholder="e.g. RELIANCE"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500 transition-colors"
                  value={symbol}
                  onChange={e => setSymbol(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-400 font-medium">Quantity</label>
                <input 
                  type="number" 
                  step="any"
                  required
                  placeholder="e.g. 100"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500 transition-colors"
                  value={quantity}
                  onChange={e => setQuantity(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-400 font-medium">Average Buy Price (₹)</label>
                <input 
                  type="number" 
                  step="any"
                  required
                  placeholder="e.g. 2500"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500 transition-colors"
                  value={price}
                  onChange={e => setPrice(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-400 font-medium">Strategy</label>
                <select 
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500 transition-colors"
                  value={frequency}
                  onChange={e => setFrequency(e.target.value)}
                >
                  <option value="Daily">Daily</option>
                  <option value="Weekly">Weekly</option>
                  <option value="Monthly">Monthly</option>
                  <option value="Yearly">Yearly</option>
                  <option value="Long-term">Long-term</option>
                </select>
              </div>
              <button 
                type="submit"
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm py-2 rounded-lg transition-colors mt-2"
              >
                Add to Portfolio
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
