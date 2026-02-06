# Stock Picker - Nifty 500 Discovery & AI Chat

A comprehensive stock discovery platform for the Indian equity market (Nifty 500) with an AI-powered financial expert assistant.

## Features

### Discovery Page
- **Market Pulse**: Real-time market breadth and sentiment analysis
- **Sector Performance**: 11 sector performance grid with visual indicators
- **Smart Buckets**: 8 data-driven stock discovery buckets:
  - Momentum Leaders (highest 30-day returns)
  - Beaten Down (oversold opportunities)
  - Volume Surge (unusual volume activity)
  - Revenue Rockets (top revenue growth)
  - Profit Machines (highest profit margins)
  - Near 52-Week High
  - Near 52-Week Low
  - Sector Outperformers
- **Top Movers**: Daily gainers and losers

### AI Chat (Nifty Sage)
- Natural language queries about stocks and markets
- ReAct-style agent with 13 specialized tools
- Real-time streaming responses
- Powered by OpenAI GPT-4o

## Tech Stack

### Backend
- **Python 3.12+** with FastAPI
- **SQLite** for data storage
- **OpenAI API** for AI chat
- **uv** package manager

### Frontend
- **Next.js 16** with App Router
- **TypeScript**
- **Tailwind CSS** + **shadcn/ui**
- **Recharts** for sparkline charts

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+
- uv package manager (`pip install uv`)
- OpenAI API key (for AI chat)

### Backend Setup

```bash
cd stock-picker

# Install dependencies
uv sync

# Create .env file
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run data pipeline (first time only)
uv run python main.py fetch-list
uv run python main.py fetch-prices
uv run python main.py fetch-financials
uv run python main.py fetch-news

# Start API server
uv run python main.py serve
```

### Frontend Setup

```bash
cd stock-picker-web

# Install dependencies
npm install

# Start development server
npm run dev
```

### Access the App
- **Discovery Page**: http://localhost:3000
- **AI Chat**: http://localhost:3000/chat
- **API Docs**: http://localhost:8000/docs

## API Endpoints

### Discovery
- `GET /api/discovery/market-pulse` - Market breadth and sentiment
- `GET /api/discovery/sectors` - Sector performance
- `GET /api/discovery/buckets` - All stock buckets
- `GET /api/discovery/movers` - Top gainers/losers

### Stocks
- `GET /api/stocks/search?q=` - Search stocks
- `GET /api/stocks/{symbol}` - Stock details
- `GET /api/stocks/{symbol}/prices` - Price history
- `GET /api/stocks/{symbol}/financials` - Financial data

### Chat
- `POST /api/chat` - AI chat with SSE streaming

## Project Structure

```
stock-picker/
├── main.py              # CLI entry point
├── api_server.py        # FastAPI app
├── api_routes/          # API endpoints
├── discovery_engine.py  # Bucket computations
├── data_store.py        # SQLite queries
├── agent.py             # AI agent (ReAct loop)
├── agent_tools.py       # 13 tool definitions
├── agent_prompts.py     # System prompts
├── fetch_*.py           # Data pipeline scripts
└── data/                # SQLite database

stock-picker-web/
├── src/app/             # Next.js pages
├── src/components/      # React components
├── src/lib/             # API client & types
└── public/              # Static assets
```

## Environment Variables

### Backend (.env)
```
OPENAI_API_KEY=your-api-key-here
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Deployment

See deployment guides for:
- **Backend**: Railway, Render, or any Docker host
- **Frontend**: Vercel (recommended for Next.js)

## License

MIT
