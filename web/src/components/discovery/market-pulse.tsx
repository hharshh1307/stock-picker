"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Activity } from "lucide-react";
import type { MarketPulse } from "@/lib/types";

interface MarketPulseProps {
  data: MarketPulse;
}

export function MarketPulseCard({ data }: MarketPulseProps) {
  const advancingPct = (data.advancing_30d / data.total_stocks) * 100;
  const decliningPct = (data.declining_30d / data.total_stocks) * 100;

  const sentimentColors: Record<string, string> = {
    STRONGLY_BULLISH: "text-emerald-400",
    BULLISH: "text-emerald-500",
    NEUTRAL: "text-zinc-400",
    BEARISH: "text-red-500",
    STRONGLY_BEARISH: "text-red-400",
  };

  const sentimentLabels: Record<string, string> = {
    STRONGLY_BULLISH: "Strongly Bullish",
    BULLISH: "Bullish",
    NEUTRAL: "Neutral",
    BEARISH: "Bearish",
    STRONGLY_BEARISH: "Strongly Bearish",
  };

  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Activity className="h-5 w-5 text-zinc-400" />
          Market Pulse
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Sentiment */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-400">30-Day Sentiment</span>
            <span className={`font-semibold ${sentimentColors[data.sentiment]}`}>
              {sentimentLabels[data.sentiment]}
            </span>
          </div>

          {/* Breadth Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-zinc-400">
              <span className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3 text-emerald-500" />
                {data.advancing_30d} advancing
              </span>
              <span className="flex items-center gap-1">
                {data.declining_30d} declining
                <TrendingDown className="h-3 w-3 text-red-500" />
              </span>
            </div>
            <div className="h-3 rounded-full bg-zinc-800 overflow-hidden flex">
              <div
                className="bg-emerald-500 transition-all"
                style={{ width: `${advancingPct}%` }}
              />
              <div
                className="bg-red-500 transition-all"
                style={{ width: `${decliningPct}%` }}
              />
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-4 pt-2">
            <div className="text-center">
              <div className="text-2xl font-bold">{data.total_stocks}</div>
              <div className="text-xs text-zinc-500">Stocks</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{data.breadth_ratio_30d.toFixed(2)}</div>
              <div className="text-xs text-zinc-500">Breadth Ratio</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold ${data.index_change_30d >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                {data.index_change_30d >= 0 ? '+' : ''}{data.index_change_30d.toFixed(1)}%
              </div>
              <div className="text-xs text-zinc-500">Index 30D</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
