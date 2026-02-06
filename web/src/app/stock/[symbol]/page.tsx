import { api, formatINR, formatCrores, formatPercent, formatVolume } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChangeBadge } from "@/components/shared/change-badge";
import { Sparkline } from "@/components/shared/sparkline";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ArrowLeft, TrendingUp, TrendingDown, BarChart3, Newspaper } from "lucide-react";
import Link from "next/link";

export const dynamic = "force-dynamic";

interface StockPageProps {
  params: Promise<{ symbol: string }>;
}

async function getStockData(symbol: string) {
  try {
    const [detail, financials, news] = await Promise.all([
      api.stocks.getDetail(symbol),
      api.stocks.getFinancials(symbol),
      api.stocks.getNews(symbol, 10),
    ]);
    return { detail, financials, news, error: null };
  } catch (error) {
    console.error("Failed to fetch stock data:", error);
    return { detail: null, financials: null, news: null, error: "Failed to load stock data" };
  }
}

export default async function StockPage({ params }: StockPageProps) {
  const { symbol } = await params;
  const { detail, financials, news, error } = await getStockData(symbol.toUpperCase());

  if (error || !detail) {
    return (
      <div className="p-8">
        <Link href="/" className="flex items-center gap-2 text-zinc-400 hover:text-zinc-100 mb-6">
          <ArrowLeft className="h-4 w-4" /> Back to Discovery
        </Link>
        <div className="rounded-lg bg-red-900/20 border border-red-800 p-6 text-center">
          <h2 className="text-xl font-semibold text-red-400">Stock Not Found</h2>
          <p className="mt-2 text-zinc-400">{error || `Could not find data for ${symbol}`}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      {/* Back Link */}
      <Link href="/" className="flex items-center gap-2 text-zinc-400 hover:text-zinc-100">
        <ArrowLeft className="h-4 w-4" /> Back to Discovery
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold">{detail.symbol}</h1>
            {detail.sector && (
              <Badge variant="outline">{detail.sector}</Badge>
            )}
          </div>
          <p className="text-zinc-400 mt-1">{detail.company_name}</p>
          {detail.industry && (
            <p className="text-zinc-500 text-sm">{detail.industry}</p>
          )}
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold">{formatINR(detail.latest_price)}</div>
          <ChangeBadge value={detail.ytd_return} className="text-lg" />
          <div className="text-xs text-zinc-500 mt-1">YTD Return</div>
        </div>
      </div>

      {/* Price Chart & Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg">30-Day Price Chart</CardTitle>
          </CardHeader>
          <CardContent>
            <Sparkline data={detail.sparkline_data} height={200} />
          </CardContent>
        </Card>

        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg">Key Stats</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-zinc-500">Open</div>
                <div className="font-medium">{formatINR(detail.open)}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500">Volume</div>
                <div className="font-medium">{formatVolume(detail.volume)}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500">Day High</div>
                <div className="font-medium text-emerald-500">{formatINR(detail.high)}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-500">Day Low</div>
                <div className="font-medium text-red-500">{formatINR(detail.low)}</div>
              </div>
            </div>

            <div className="border-t border-zinc-700 pt-4">
              <div className="text-xs text-zinc-500 mb-2">52-Week Range</div>
              <div className="flex items-center gap-2">
                <span className="text-sm">{formatINR(detail.low_52w)}</span>
                <div className="flex-1 h-2 bg-zinc-700 rounded-full relative">
                  <div
                    className="absolute h-2 w-2 bg-emerald-500 rounded-full -top-0"
                    style={{
                      left: detail.high_52w && detail.low_52w && detail.latest_price
                        ? `${((detail.latest_price - detail.low_52w) / (detail.high_52w - detail.low_52w)) * 100}%`
                        : "50%",
                    }}
                  />
                </div>
                <span className="text-sm">{formatINR(detail.high_52w)}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Financials & News */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Financials */}
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-zinc-400" />
              Quarterly Financials
            </CardTitle>
          </CardHeader>
          <CardContent>
            {financials && financials.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Period</TableHead>
                    <TableHead className="text-right">Revenue</TableHead>
                    <TableHead className="text-right">Net Income</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {financials.slice(0, 4).map((q) => (
                    <TableRow key={q.period} className="hover:bg-zinc-800/50">
                      <TableCell className="font-medium">{q.period}</TableCell>
                      <TableCell className="text-right">{formatCrores(q.revenue)}</TableCell>
                      <TableCell className="text-right">
                        <span className={q.net_income && q.net_income >= 0 ? "text-emerald-500" : "text-red-500"}>
                          {formatCrores(q.net_income)}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-zinc-500 text-sm">No financial data available</p>
            )}
          </CardContent>
        </Card>

        {/* News */}
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Newspaper className="h-5 w-5 text-zinc-400" />
              Recent News
            </CardTitle>
          </CardHeader>
          <CardContent>
            {news && news.length > 0 ? (
              <div className="space-y-4">
                {news.slice(0, 5).map((item, idx) => (
                  <a
                    key={idx}
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block hover:bg-zinc-800/50 rounded-lg p-2 -mx-2 transition-colors"
                  >
                    <h4 className="text-sm font-medium line-clamp-2">{item.title}</h4>
                    <div className="flex items-center gap-2 mt-1 text-xs text-zinc-500">
                      <span>{item.source_name}</span>
                      {item.published_at && (
                        <>
                          <span>·</span>
                          <span>{new Date(item.published_at).toLocaleDateString()}</span>
                        </>
                      )}
                    </div>
                  </a>
                ))}
              </div>
            ) : (
              <p className="text-zinc-500 text-sm">No recent news</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
