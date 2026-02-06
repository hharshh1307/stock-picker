// API Response Types

export interface MarketPulse {
  sentiment: 'STRONGLY_BULLISH' | 'BULLISH' | 'NEUTRAL' | 'BEARISH' | 'STRONGLY_BEARISH';
  breadth_ratio_30d: number;
  breadth_ratio_7d: number;
  advancing_30d: number;
  declining_30d: number;
  advancing_7d: number;
  declining_7d: number;
  total_stocks: number;
  index_change_30d: number;
}

export interface SectorSummary {
  sector: string;
  avg_return: number;
  stock_count: number;
  top_stock: string | null;
  top_stock_return: number | null;
}

export interface BucketStock {
  symbol: string;
  company_name: string;
  sector: string | null;
  industry: string | null;
  metric_value: number;
  metric_label: string;
  latest_price: number;
  change_pct: number;
  sparkline_data: number[];
}

export interface Bucket {
  bucket_id: string;
  name: string;
  description: string;
  stocks: BucketStock[];
  stock_count: number;
  preview_count?: number;
}

export interface Mover {
  symbol: string;
  company_name: string;
  sector: string;
  change_pct: number;
  start_price: number;
  end_price: number;
  sparkline_data: number[];
}

export interface MoversData {
  gainers: Mover[];
  losers: Mover[];
}

export interface StockDetail {
  symbol: string;
  yahoo_symbol: string;
  company_name: string;
  sector: string | null;
  industry: string | null;
  latest_price: number | null;
  latest_date: string | null;
  open: number | null;
  high: number | null;
  low: number | null;
  volume: number | null;
  high_52w: number | null;
  low_52w: number | null;
  ytd_return: number | null;
  sparkline_data: number[];
}

export interface StockSearchResult {
  symbol: string;
  company_name: string;
  sector: string | null;
  industry: string | null;
}

export interface PricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface FinancialQuarter {
  period: string;
  revenue: number | null;
  net_income: number | null;
  ebitda: number | null;
  total_assets: number | null;
  total_debt: number | null;
  total_equity: number | null;
  operating_cashflow: number | null;
  free_cashflow: number | null;
}

export interface NewsItem {
  title: string;
  url: string;
  source_name: string;
  published_at: string | null;
  description: string | null;
}

export interface ChatSuggestion {
  question: string;
  category: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
}

export interface ChatStreamEvent {
  type: 'text' | 'tool_call' | 'tool_result' | 'done' | 'error';
  content?: string;
  tool?: string;
  arguments?: Record<string, unknown>;
  result_preview?: string;
}
