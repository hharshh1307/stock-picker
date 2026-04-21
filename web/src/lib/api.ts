// API client for the stock-picker backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

// Discovery endpoints
export const api = {
  discovery: {
    getMarketPulse: () =>
      fetchAPI<import('./types').MarketPulse>('/api/discovery/market-pulse'),

    getSectors: () =>
      fetchAPI<import('./types').SectorSummary[]>('/api/discovery/sectors'),

    getBuckets: (previewLimit = 6) =>
      fetchAPI<import('./types').Bucket[]>(`/api/discovery/buckets?preview_limit=${previewLimit}`),

    getBucket: (bucketId: string, limit = 50) =>
      fetchAPI<import('./types').Bucket>(`/api/discovery/bucket/${bucketId}?limit=${limit}`),

    getMovers: (limit = 10) =>
      fetchAPI<import('./types').MoversData>(`/api/discovery/movers?limit=${limit}`),
  },

  stocks: {
    search: (query: string, limit = 20) =>
      fetchAPI<import('./types').StockSearchResult[]>(`/api/stocks/search?q=${encodeURIComponent(query)}&limit=${limit}`),

    getDetail: (symbol: string) =>
      fetchAPI<import('./types').StockDetail>(`/api/stocks/${symbol}`),

    getPrices: (symbol: string, days = 365) =>
      fetchAPI<import('./types').PricePoint[]>(`/api/stocks/${symbol}/prices?days=${days}`),

    getFinancials: (symbol: string) =>
      fetchAPI<import('./types').FinancialQuarter[]>(`/api/stocks/${symbol}/financials`),

    getNews: (symbol: string, limit = 20) =>
      fetchAPI<import('./types').NewsItem[]>(`/api/stocks/${symbol}/news?limit=${limit}`),
  },

  chat: {
    getSuggestions: () =>
      fetchAPI<import('./types').ChatSuggestion[]>('/api/chat/suggestions'),

    // For SSE streaming, we need to handle this differently
    streamChat: async function* (message: string, conversationId?: string) {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, conversation_id: conversationId }),
      });

      if (!res.ok) {
        throw new Error(`Chat error: ${res.status}`);
      }

      const reader = res.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              yield data as import('./types').ChatStreamEvent;
            } catch {
              // Skip invalid JSON
            }
          }
        }
      }
    },
  },

  user: {
    getProfile: () =>
      fetchAPI<import('./types').UserProfile>('/api/user/profile'),
    
    updateProfile: (profile: import('./types').UserProfile) =>
      fetchAPI<{status: string}>('/api/user/profile', {
        method: 'POST',
        body: JSON.stringify(profile),
      }),
      
    getPlans: () =>
      fetchAPI<import('./types').InvestmentPlan[]>('/api/user/plans'),
      
    upsertPlan: (plan: import('./types').InvestmentPlan) =>
      fetchAPI<{status: string}>('/api/user/plans', {
        method: 'POST',
        body: JSON.stringify(plan),
      }),
      
    deletePlan: (id: number) =>
      fetchAPI<{status: string}>(`/api/user/plans/${id}`, { method: 'DELETE' }),
      
    getPortfolio: () =>
      fetchAPI<import('./types').PortfolioItem[]>('/api/user/portfolio'),
      
    upsertPortfolioItem: (item: import('./types').PortfolioItem) =>
      fetchAPI<{status: string}>('/api/user/portfolio', {
        method: 'POST',
        body: JSON.stringify(item),
      }),
      
    deletePortfolioItem: (id: number) =>
      fetchAPI<{status: string}>(`/api/user/portfolio/${id}`, { method: 'DELETE' }),
  },
};

// Format helpers
export function formatINR(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatCrores(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  const crores = value / 10000000;
  if (Math.abs(crores) >= 1000) {
    return `₹${(crores / 1000).toFixed(2)}K Cr`;
  }
  return `₹${crores.toFixed(2)} Cr`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}

export function formatVolume(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  if (value >= 10000000) return `${(value / 10000000).toFixed(2)} Cr`;
  if (value >= 100000) return `${(value / 100000).toFixed(2)} L`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return value.toString();
}
