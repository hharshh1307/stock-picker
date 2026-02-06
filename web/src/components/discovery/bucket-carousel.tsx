"use client";

import Link from "next/link";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { StockCard } from "./stock-card";
import { ChevronRight } from "lucide-react";
import type { Bucket } from "@/lib/types";

interface BucketCarouselProps {
  bucket: Bucket;
}

export function BucketCarousel({ bucket }: BucketCarouselProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">{bucket.name}</h3>
          <p className="text-sm text-zinc-400">{bucket.description}</p>
        </div>
        <Link
          href={`/bucket/${bucket.bucket_id}`}
          className="flex items-center gap-1 text-sm text-zinc-400 hover:text-zinc-100 transition-colors"
        >
          See all {bucket.stock_count}
          <ChevronRight className="h-4 w-4" />
        </Link>
      </div>

      <ScrollArea className="w-full whitespace-nowrap">
        <div className="flex gap-4 pb-4">
          {bucket.stocks.map((stock) => (
            <div key={stock.symbol} className="w-[200px] flex-none">
              <StockCard stock={stock} />
            </div>
          ))}
        </div>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>
    </div>
  );
}
