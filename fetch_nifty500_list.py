import time
from datetime import datetime

import yfinance as yf

from config import YFINANCE_BATCH_SIZE, YFINANCE_BATCH_DELAY_SEC, UNIVERSE_INDICES
from data_store import DataStore
from models import Stock, FetchLog, FetchStatus, DataSource
from ticker_mapping import nse_to_yahoo
from utils import setup_logger, RateLimiter

logger = setup_logger(__name__, "fetch_nifty500_list.log")


def get_nifty500_symbols() -> list[str]:
    """Fetch ALL active NSE listed equities (thousands of stocks)."""
    try:
        from nselib import capital_market
        df = capital_market.equity_list()
        
        # Filter out ETFs and non-equities if possible, typically 'SERIES' == 'EQ'
        if 'SERIES' in df.columns:
            df = df[df['SERIES'] == 'EQ']
            
        if 'SYMBOL' in df.columns:
            syms = df['SYMBOL'].tolist()
            logger.info(f"Got {len(syms)} symbols from nselib active equity list")
            return syms
    except Exception as e:
        logger.warning(f"Failed to fetch active equities from nselib: {e}")

    # Fallback to nifty 500
    try:
        from niftystocks import ns
        return ns.get_nifty500()
    except:
        pass

    raise RuntimeError("Could not fetch equity list from any source")


def enrich_stock_info(
    symbols: list[str], store: DataStore
) -> list[Stock]:
    """Fetch company name, sector, industry from yfinance for each symbol."""
    stocks: list[Stock] = []
    rate_limiter = RateLimiter(min_delay=1.0, max_delay=2.0)
    failed: list[str] = []

    for i, symbol in enumerate(symbols):
        yahoo_sym = nse_to_yahoo(symbol)
        try:
            rate_limiter.wait()
            ticker = yf.Ticker(yahoo_sym)
            info = ticker.info or {}
            stock = Stock(
                symbol=symbol,
                yahoo_symbol=yahoo_sym,
                company_name=info.get("longName") or info.get("shortName") or symbol,
                sector=info.get("sector"),
                industry=info.get("industry"),
                last_updated=datetime.now(),
            )
            stocks.append(stock)
            if (i + 1) % 50 == 0:
                logger.info(f"Enriched {i + 1}/{len(symbols)} stocks")
                # Save intermediate progress
                store.upsert_stocks(stocks[-50:])
        except Exception as e:
            logger.warning(f"Failed to enrich {symbol}: {e}")
            failed.append(symbol)
            # Still add the stock with minimal info
            stocks.append(
                Stock(
                    symbol=symbol,
                    yahoo_symbol=yahoo_sym,
                    company_name=symbol,
                    last_updated=datetime.now(),
                )
            )

    if failed:
        logger.warning(f"Failed to enrich {len(failed)} stocks: {failed[:10]}...")

    return stocks


def _nselib_index(fn_name: str) -> tuple[list[str], dict[str, dict]]:
    """Fetch an official NSE index constituent list. Returns (symbols, meta)."""
    from nselib import capital_market
    df = getattr(capital_market, fn_name)()
    if df is None or df.empty or "Symbol" not in df.columns:
        return [], {}
    syms = df["Symbol"].astype(str).str.strip().tolist()
    meta = {}
    if "Company Name" in df.columns:
        for _, r in df.iterrows():
            meta[str(r["Symbol"]).strip()] = {
                "company_name": r.get("Company Name"),
                "industry": r.get("Industry"),
            }
    return syms, meta


def get_active_nse_symbols() -> set[str]:
    """Current NSE EQ tickers, straight from the exchange.

    Critical for correctness: the index constituent lists (niftystocks, and
    the nselib index lists) carry *stale* pre-merger/pre-rename tickers, e.g.
    LTI and MINDTREE (both -> LTIM), HDFC (-> HDFCBANK), IDFC (-> IDFCFINBANK),
    TATAMOTORS (-> TMPV), SHRIRAMCIT, PVR, WELSPUNIND. Those return zero price
    data forever and are not tradable, so the universe is intersected with the
    live exchange list.
    """
    from nselib import capital_market
    df = capital_market.equity_list()
    if "SERIES" in df.columns:
        df = df[df["SERIES"] == "EQ"]
    return {str(s).strip() for s in df["SYMBOL"].tolist() if str(s).strip()}


def get_nifty500_symbols() -> list[str]:
    """
    Fetch the configured index universe (default: Nifty 500 + Nifty Midcap 150).

    Deliberately NOT every NSE-listed equity: the full list is ~2,600 names,
    takes over an hour to enrich, and is dominated by microcaps that cannot be
    traded at size. Returns a de-duplicated, order-preserving symbol list,
    restricted to tickers the exchange still lists.
    """
    from config import UNIVERSE_INDICES

    all_syms: list[str] = []
    for idx in UNIVERSE_INDICES:
        try:
            if idx == "nifty500":
                from niftystocks import ns
                syms = list(ns.get_nifty500())
                logger.info(f"{idx}: {len(syms)} symbols")
            elif idx.startswith("nifty") and idx not in ("nifty500",):
                # nselib exposes official NSE constituent lists by function name
                syms, _ = _nselib_index(f"{idx}_equity_list")
                logger.info(f"{idx}: {len(syms)} symbols")
            else:
                logger.warning(f"Unknown universe index: {idx}")
                continue
            all_syms.extend(syms)
        except Exception as e:
            logger.warning(f"Failed to fetch {idx}: {e}")

    if not all_syms:
        # Last-resort fallback so the pipeline is never left with an empty universe
        try:
            all_syms = sorted(get_active_nse_symbols())
            logger.warning(f"Falling back to full NSE equity list: {len(all_syms)} symbols")
        except Exception as e:
            raise RuntimeError(f"Could not fetch any universe: {e}")
        return all_syms

    # Keep only tickers NSE still actively lists.
    try:
        active = get_active_nse_symbols()
        before = len(set(all_syms))
        all_syms = [s for s in all_syms if s.strip() in active]
        stale = before - len(set(all_syms))
        logger.info(
            f"Dropped {stale} stale/renamed tickers not currently NSE-listed "
            f"({before} -> {len(set(all_syms))})"
        )
    except Exception as e:
        logger.warning(
            f"Could not verify against the live NSE list ({e}); "
            f"stale tickers may slip through"
        )

    seen: set[str] = set()
    deduped: list[str] = []
    for s in all_syms:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped


def get_official_meta() -> dict[str, dict]:
    """Company name / industry from official NSE index lists, where available."""
    meta: dict[str, dict] = {}
    for idx in UNIVERSE_INDICES:
        if idx == "nifty500":
            continue
        try:
            _, m = _nselib_index(f"{idx}_equity_list")
            meta.update(m)
        except Exception:
            continue
    return meta


def run(store: DataStore, skip_enrichment: bool = False) -> dict:
    """Fetch the configured index universe and store it.

    Returns summary dict with counts.
    """
    started = datetime.now()
    logger.info(f"Fetching index universe {UNIVERSE_INDICES}...")

    symbols = get_nifty500_symbols()
    logger.info(f"Universe resolved to {len(symbols)} symbols")

    if skip_enrichment:
        meta = get_official_meta()
        stocks = []
        for s in symbols:
            m = meta.get(s, {})
            stocks.append(
                Stock(
                    symbol=s,
                    yahoo_symbol=nse_to_yahoo(s),
                    company_name=m.get("company_name") or s,
                    industry=m.get("industry"),
                    last_updated=datetime.now(),
                )
            )
    else:
        logger.info("Enriching stocks with company info from yfinance (this takes a few minutes)...")
        stocks = enrich_stock_info(symbols, store)

    count = store.upsert_stocks(stocks)
    logger.info(f"Stored {count} stocks in database")

    store.log_fetch(
        FetchLog(
            script_name="fetch_nifty500_list",
            symbol=None,
            status=FetchStatus.SUCCESS,
            records_fetched=count,
            source=DataSource.NIFTYSTOCKS,
            started_at=started,
            completed_at=datetime.now(),
        )
    )

    return {"total": len(symbols), "stored": count}


if __name__ == "__main__":
    store = DataStore()
    try:
        result = run(store)
        print(f"Done. Stored {result['stored']}/{result['total']} stocks.")
    finally:
        store.close()
