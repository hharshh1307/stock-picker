"use client";

import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkline } from "@/components/shared/sparkline";
import { ChangeBadge } from "@/components/shared/change-badge";
import { formatINR } from "@/lib/api";
import type { BucketStock } from "@/lib/types";

interface StockCardProps {
  stock: BucketStock;
}

export function StockCard({ stock }: StockCardProps) {
  return (
    <Link href={`/stock/${stock.symbol}`}>
      <Card className="bg-zinc-800/50 border-zinc-700/50 hover:bg-zinc-800 hover:border-zinc-600 transition-all cursor-pointer h-full">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h4 className="font-semibold text-sm">{stock.symbol}</h4>
              <p className="text-xs text-zinc-400 truncate max-w-[120px]">
                {stock.company_name}
              </p>
            </div>
            <ChangeBadge value={stock.change_pct} showIcon={false} className="text-sm" />
          </div>

          <div className="mt-3">
            <Sparkline data={stock.sparkline_data} height={36} />
          </div>

          <div className="mt-3 flex items-center justify-between">
            <span className="text-sm font-medium">
              {formatINR(stock.latest_price)}
            </span>
            {stock.sector && (
              <Badge variant="outline" className="text-xs px-1.5 py-0 max-w-[80px] truncate">
                {stock.sector}
              </Badge>
            )}
          </div>

          <div className="mt-2 pt-2 border-t border-zinc-700/50">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span>{stock.metric_label}</span>
              <span className={stock.metric_value >= 0 ? "text-emerald-500" : "text-red-500"}>
                {stock.metric_value >= 0 ? "+" : ""}{stock.metric_value}
                {stock.metric_label.includes("%") ? "" : "%"}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
