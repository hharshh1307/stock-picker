"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChangeBadge } from "@/components/shared/change-badge";
import { PieChart } from "lucide-react";
import type { SectorSummary } from "@/lib/types";

interface SectorGridProps {
  sectors: SectorSummary[];
}

export function SectorGrid({ sectors }: SectorGridProps) {
  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <PieChart className="h-5 w-5 text-zinc-400" />
          Sector Performance (30D)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {sectors.map((sector) => (
            <div
              key={sector.sector}
              className="rounded-lg bg-zinc-800/50 p-3 hover:bg-zinc-800 transition-colors cursor-pointer"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <h4 className="text-sm font-medium truncate">{sector.sector}</h4>
                  <div className="mt-1 text-xs text-zinc-500">
                    {sector.stock_count} stocks
                  </div>
                </div>
                <ChangeBadge value={sector.avg_return} showIcon={false} className="text-sm" />
              </div>
              {sector.top_stock && (
                <div className="mt-2 pt-2 border-t border-zinc-700/50">
                  <div className="flex items-center justify-between text-xs">
                    <Badge variant="outline" className="text-xs px-1.5 py-0">
                      {sector.top_stock}
                    </Badge>
                    <span className="text-emerald-500">
                      +{sector.top_stock_return?.toFixed(1)}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
