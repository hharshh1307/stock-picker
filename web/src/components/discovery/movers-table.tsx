"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Sparkline } from "@/components/shared/sparkline";
import { ChangeBadge } from "@/components/shared/change-badge";
import { formatINR } from "@/lib/api";
import { TrendingUp, TrendingDown } from "lucide-react";
import type { MoversData } from "@/lib/types";

interface MoversTableProps {
  data: MoversData;
}

export function MoversTable({ data }: MoversTableProps) {
  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Top Movers (30D)</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="gainers" className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-4">
            <TabsTrigger value="gainers" className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-emerald-500" />
              Gainers
            </TabsTrigger>
            <TabsTrigger value="losers" className="flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-red-500" />
              Losers
            </TabsTrigger>
          </TabsList>

          <TabsContent value="gainers">
            <MoversList movers={data.gainers} type="gainer" />
          </TabsContent>

          <TabsContent value="losers">
            <MoversList movers={data.losers} type="loser" />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

interface MoversListProps {
  movers: MoversData["gainers"];
  type: "gainer" | "loser";
}

function MoversList({ movers, type }: MoversListProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Stock</TableHead>
          <TableHead className="hidden md:table-cell">Sector</TableHead>
          <TableHead className="w-[100px]">Chart</TableHead>
          <TableHead className="text-right">Price</TableHead>
          <TableHead className="text-right">Change</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {movers.map((mover) => (
          <TableRow key={mover.symbol} className="hover:bg-zinc-800/50">
            <TableCell>
              <Link href={`/stock/${mover.symbol}`} className="hover:underline">
                <div className="font-medium">{mover.symbol}</div>
                <div className="text-xs text-zinc-400 truncate max-w-[150px]">
                  {mover.company_name}
                </div>
              </Link>
            </TableCell>
            <TableCell className="hidden md:table-cell">
              <Badge variant="outline" className="text-xs">
                {mover.sector}
              </Badge>
            </TableCell>
            <TableCell>
              <Sparkline data={mover.sparkline_data} height={30} />
            </TableCell>
            <TableCell className="text-right font-medium">
              {formatINR(mover.end_price)}
            </TableCell>
            <TableCell className="text-right">
              <ChangeBadge value={mover.change_pct} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
