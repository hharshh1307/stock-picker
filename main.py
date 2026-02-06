import argparse
import sys
from datetime import datetime

from config import DB_PATH
from data_store import DataStore
from utils import setup_logger

logger = setup_logger(__name__, "pipeline.log")


def cmd_list(store: DataStore, args: argparse.Namespace) -> None:
    import fetch_nifty500_list
    skip = getattr(args, "skip_enrichment", False)
    result = fetch_nifty500_list.run(store, skip_enrichment=skip)
    print(f"Stock list: {result.get('stored', 0)}/{result.get('total', 0)} stocks stored.")


def cmd_prices(store: DataStore, args: argparse.Namespace) -> None:
    import fetch_price_data
    symbols = args.symbols.split(",") if args.symbols else None
    result = fetch_price_data.run(store, symbols=symbols, full_refresh=args.full_refresh)
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    print(
        f"Prices: {result['success']}/{result['total']} stocks, "
        f"{result['records']} records inserted, {result['failed']} failed."
    )


def cmd_financials(store: DataStore, args: argparse.Namespace) -> None:
    import fetch_financials
    symbols = args.symbols.split(",") if args.symbols else None
    result = fetch_financials.run(
        store, symbols=symbols, statement_type=args.statement_type
    )
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    print(
        f"Financials: {result['with_data']}/{result['total']} stocks with data, "
        f"{result['records']} records, {result['empty']} empty, {result['failed']} failed."
    )


def cmd_news(store: DataStore, args: argparse.Namespace) -> None:
    import fetch_news
    symbols = args.symbols.split(",") if args.symbols else None
    result = fetch_news.run(
        store,
        symbols=symbols,
        gnews_only=args.gnews_only,
        rss_only=args.rss_only,
        max_stocks=args.max_stocks,
    )
    print(
        f"News: {result['total']} articles (GNews: {result['gnews']}, RSS: {result['rss']})."
    )


def cmd_index(store: DataStore, args: argparse.Namespace) -> None:
    import fetch_index_data
    result = fetch_index_data.run(store)
    print(f"Index: {result['records']} records from {result['source']}.")


def cmd_insights(store: DataStore, args: argparse.Namespace) -> None:
    import market_intelligence
    market_intelligence.run(store)


def cmd_sectors(store: DataStore, args: argparse.Namespace) -> None:
    sectors = store.get_all_sectors()
    if not sectors:
        print("No sector data. Run 'main.py list' (without --skip-enrichment) first.")
        return
    print(f"\n  {'Sector':<35s} {'Stocks':>8s}")
    print(f"  {'-'*35} {'-'*8}")
    for s in sectors:
        print(f"  {s['sector']:<35s} {s['stock_count']:>6}")
    print(f"\n  Total: {sum(s['stock_count'] for s in sectors)} stocks across {len(sectors)} sectors")


def cmd_status(store: DataStore, args: argparse.Namespace) -> None:
    counts = store.get_table_counts()
    print("=== Database Record Counts ===")
    for table, count in counts.items():
        print(f"  {table:25s} {count:>8,}")

    pipeline = store.get_pipeline_status()
    if pipeline:
        print("\n=== Last Fetch Runs ===")
        print(f"  {'Script':<25s} {'Last Run':<22s} {'OK':>6s} {'Fail':>6s} {'Records':>10s}")
        print(f"  {'-'*25} {'-'*22} {'-'*6} {'-'*6} {'-'*10}")
        for row in pipeline:
            print(
                f"  {row['script_name']:<25s} {str(row['last_run']):<22s} "
                f"{row['success_count'] or 0:>6} {row['failed_count'] or 0:>6} "
                f"{row['total_records'] or 0:>10,}"
            )
    else:
        print("\nNo fetch runs recorded yet.")


def cmd_all(store: DataStore, args: argparse.Namespace) -> None:
    started = datetime.now()
    print("=== Running Full Pipeline ===\n")

    print("[1/5] Fetching Nifty 500 stock list...")
    cmd_list(store, args)

    print("\n[2/5] Fetching index data...")
    cmd_index(store, args)

    print("\n[3/5] Fetching price data...")
    args.symbols = None
    args.full_refresh = False
    cmd_prices(store, args)

    print("\n[4/5] Fetching quarterly financials...")
    args.statement_type = None
    cmd_financials(store, args)

    print("\n[5/5] Fetching news...")
    args.gnews_only = False
    args.rss_only = False
    args.max_stocks = 100  # Limit GNews to top 100 for full pipeline
    cmd_news(store, args)

    print(f"\n=== Pipeline Complete (duration: {datetime.now() - started}) ===")
    cmd_status(store, args)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Nifty 500 Stock Data Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db", default=str(DB_PATH), help="Path to SQLite database")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # all
    p_all = sub.add_parser("all", help="Run full pipeline")
    p_all.add_argument("--skip-enrichment", action="store_true", help="Skip yfinance info enrichment for stock list")

    # list
    p_list = sub.add_parser("list", help="Fetch/update Nifty 500 stock list")
    p_list.add_argument("--skip-enrichment", action="store_true", help="Skip yfinance info enrichment")

    # prices
    p_prices = sub.add_parser("prices", help="Fetch OHLCV price data")
    p_prices.add_argument("--symbols", type=str, help="Comma-separated NSE symbols (e.g. RELIANCE,TCS)")
    p_prices.add_argument("--full-refresh", action="store_true", help="Re-fetch all history")

    # financials
    p_fin = sub.add_parser("financials", help="Fetch quarterly financial statements")
    p_fin.add_argument("--symbols", type=str, help="Comma-separated NSE symbols")
    p_fin.add_argument("--statement-type", choices=["income", "balance_sheet", "cashflow"], help="Filter by statement type")

    # news
    p_news = sub.add_parser("news", help="Fetch news articles")
    p_news.add_argument("--symbols", type=str, help="Comma-separated NSE symbols for GNews")
    p_news.add_argument("--gnews-only", action="store_true", help="Only fetch from GNews")
    p_news.add_argument("--rss-only", action="store_true", help="Only fetch from RSS feeds")
    p_news.add_argument("--max-stocks", type=int, help="Limit GNews to N stocks")

    # index
    sub.add_parser("index", help="Fetch Nifty 500 index data")

    # insights
    sub.add_parser("insights", help="Generate market intelligence report (trending sectors, movers, highlights)")

    # sectors
    sub.add_parser("sectors", help="List all sectors and stock counts")

    # status
    sub.add_parser("status", help="Show pipeline status and record counts")

    # serve (API server)
    p_serve = sub.add_parser("serve", help="Start the API server")
    p_serve.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    p_serve.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    p_serve.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    # chat (CLI chat interface)
    p_chat = sub.add_parser("chat", help="Start interactive AI chat session")
    p_chat.add_argument("--model", default="gpt-4o", help="OpenAI model to use (default: gpt-4o)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    # Commands that don't need DataStore
    if args.command == "serve":
        from api_server import run_server
        print(f"Starting API server on {args.host}:{args.port}...")
        run_server(host=args.host, port=args.port, reload=args.reload)
        return

    if args.command == "chat":
        from chat import run_chat
        run_chat(model=args.model, db_path=args.db)
        return

    # Commands that need DataStore
    store = DataStore(db_path=args.db)
    try:
        commands = {
            "all": cmd_all,
            "list": cmd_list,
            "prices": cmd_prices,
            "financials": cmd_financials,
            "news": cmd_news,
            "index": cmd_index,
            "insights": cmd_insights,
            "sectors": cmd_sectors,
            "status": cmd_status,
        }
        commands[args.command](store, args)
    finally:
        store.close()


if __name__ == "__main__":
    main()
