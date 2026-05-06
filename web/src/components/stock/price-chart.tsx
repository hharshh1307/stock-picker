"use client";

import { useState, useEffect } from "react";
import { api, formatINR } from "@/lib/api";
import { PricePoint } from "@/lib/types";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Loader2 } from "lucide-react";

export function PriceChart({ symbol }: { symbol: string }) {
  const [data, setData] = useState<PricePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<"1W" | "1M" | "6M" | "1Y">("1Y");

  useEffect(() => {
    async function fetchPrices() {
      setLoading(true);
      try {
        const days = period === "1W" ? 7 : period === "1M" ? 30 : period === "6M" ? 180 : 365;
        const result = await api.stocks.getPrices(symbol, days);
        setData(result);
      } catch (err) {
        console.error("Failed to load prices", err);
      } finally {
        setLoading(false);
      }
    }
    fetchPrices();
  }, [symbol, period]);

  // Format date for XAxis
  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    if (period === "1W" || period === "1M") {
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    }
    return d.toLocaleDateString(undefined, { month: "short", year: "2-digit" });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        {["1W", "1M", "6M", "1Y"].map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p as any)}
            className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
              period === p
                ? "bg-emerald-500 text-white"
                : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="h-[300px] w-full relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-zinc-900/50 z-10">
            <Loader2 className="h-6 w-6 animate-spin text-emerald-500" />
          </div>
        )}
        
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                stroke="#a1a1aa"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                minTickGap={30}
              />
              <YAxis
                domain={['auto', 'auto']}
                tickFormatter={(value) => `₹${value}`}
                stroke="#a1a1aa"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                width={60}
              />
              <Tooltip
                contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", borderRadius: "8px" }}
                itemStyle={{ color: "#10b981" }}
                labelStyle={{ color: "#a1a1aa", marginBottom: "4px" }}
                formatter={(value: number) => [formatINR(value), "Price"]}
                labelFormatter={(label) => new Date(label).toLocaleDateString()}
              />
              <Line
                type="monotone"
                dataKey="close"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 6, fill: "#10b981", stroke: "#047857" }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : !loading && (
          <div className="flex h-full items-center justify-center text-zinc-500">
            No price data available for this period.
          </div>
        )}
      </div>
    </div>
  );
}
