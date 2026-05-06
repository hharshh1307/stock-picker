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
  latest_price: number | null;
  change_1d_pct: number | null;
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

export interface UserProfile {
  risk_tolerance: string;
  total_capital: number;
  expected_returns: number;
}

export interface InvestmentPlan {
  id?: number;
  frequency: string;
  allocated_amount: number;
  description?: string;
}

export interface PortfolioItem {
  id?: number;
  symbol: string;
  quantity: number;
  average_buy_price: number;
  strategy_frequency?: string;
  added_at?: string;
  is_live_synced?: boolean;
}

export interface PortfolioItemWithPnL {
  symbol: string;
  company_name: string;
  sector: string | null;
  quantity: number;
  average_buy_price: number;
  strategy_frequency: string;
  // Price
  latest_price: number | null;
  price_date: string | null;
  high_52w: number | null;
  low_52w: number | null;
  // P&L
  invested_value: number;
  current_value: number | null;
  unrealized_pnl: number | null;
  pnl_pct: number | null;
  change_30d_pct: number | null;
  // Groww extras
  isin: string | null;
  t1_quantity: number | null;
  demat_free_quantity: number | null;
  is_live_synced: boolean;
}

export interface PortfolioPnLResponse {
  source: string;
  account_info: {
    ucc: string | null;
    active_segments: string[];
    ddpi_enabled: boolean | null;
  } | null;
  available_cash: number | null;
  summary: {
    holding_count: number;
    total_invested: number;
    total_current_value: number | null;
    total_unrealized_pnl: number | null;
    total_pnl_pct: number | null;
  };
  holdings: PortfolioItemWithPnL[];
}
