import os
import json
import numpy as np
from functools import lru_cache
from config import DATA_DIR
from data_store import DataStore

from dotenv import load_dotenv
load_dotenv()

EMBEDDINGS_FILE = DATA_DIR / "stock_embeddings.json"

_embeddings_cache = None
_stocks_cache = None


def _get_openai_client():
    from openai import OpenAI
    return OpenAI(
        api_key=os.getenv("GEMINI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )


@lru_cache(maxsize=1000)
def get_embedding(text: str) -> np.ndarray:
    client = _get_openai_client()
    response = client.embeddings.create(
        input=text,
        model="gemini-embedding-2"
    )
    return np.array(response.data[0].embedding, dtype=np.float32)


def build_embeddings():
    """Generate and save embeddings for all stocks in the database."""
    print("Building semantic search embeddings...")
    store = DataStore()
    stocks = store.get_all_stocks()
    store.close()

    texts = []
    symbols = []
    for stock in stocks:
        texts.append(f"{stock.symbol} {stock.company_name} {stock.sector or ''} {stock.industry or ''}")
        symbols.append(stock.symbol)

    client = _get_openai_client()
    # Batch in chunks of 500 (API limit)
    embeddings = {}
    for i in range(0, len(texts), 500):
        batch_texts = texts[i:i+500]
        batch_symbols = symbols[i:i+500]
        response = client.embeddings.create(input=batch_texts, model="gemini-embedding-2")
        for j, emb in enumerate(response.data):
            embeddings[batch_symbols[j]] = emb.embedding
        print(f"  Embedded {min(i+500, len(texts))}/{len(texts)} stocks...")

    with open(EMBEDDINGS_FILE, "w") as f:
        json.dump(embeddings, f)
    print(f"Saved {len(embeddings)} embeddings to {EMBEDDINGS_FILE}")


def update_embeddings_incremental():
    """
    Add embeddings only for stocks not yet in the file.
    Safe to call regularly — only calls OpenAI for new/missing symbols.
    """
    store = DataStore()
    all_stocks = {s.symbol: s for s in store.get_all_stocks()}
    store.close()

    # Load existing
    existing: dict = {}
    if EMBEDDINGS_FILE.exists():
        with open(EMBEDDINGS_FILE, "r") as f:
            existing = json.load(f)

    missing_symbols = [sym for sym in all_stocks if sym not in existing]
    if not missing_symbols:
        print("Embeddings are up-to-date — no new stocks to embed.")
        return

    print(f"Embedding {len(missing_symbols)} new stocks...")
    texts = [
        f"{s} {all_stocks[s].company_name} {all_stocks[s].sector or ''} {all_stocks[s].industry or ''}"
        for s in missing_symbols
    ]

    client = _get_openai_client()
    for i in range(0, len(texts), 500):
        batch_texts = texts[i:i+500]
        batch_symbols = missing_symbols[i:i+500]
        response = client.embeddings.create(input=batch_texts, model="gemini-embedding-2")
        for j, emb in enumerate(response.data):
            existing[batch_symbols[j]] = emb.embedding
        print(f"  Embedded {min(i+500, len(texts))}/{len(texts)}...")

    with open(EMBEDDINGS_FILE, "w") as f:
        json.dump(existing, f)
    print(f"Updated embeddings file: now has {len(existing)} stocks.")

    # Invalidate in-memory cache so next search reloads
    global _embeddings_cache, _stocks_cache
    _embeddings_cache = None
    _stocks_cache = None


def load_embeddings():
    global _embeddings_cache, _stocks_cache
    if not EMBEDDINGS_FILE.exists():
        build_embeddings()

    with open(EMBEDDINGS_FILE, "r") as f:
        data = json.load(f)

    store = DataStore()
    stocks = {s.symbol: s for s in store.get_all_stocks()}
    store.close()

    _stocks_cache = []
    _embeddings_list = []

    for symbol, emb in data.items():
        if symbol in stocks:
            _stocks_cache.append(stocks[symbol])
            _embeddings_list.append(emb)

    _embeddings_cache = np.array(_embeddings_list, dtype=np.float32)


def _sql_fallback_search(query: str, limit: int, already_found: set) -> list:
    """
    SQL LIKE search for exact symbol/name prefix matches.
    Catches stocks that have no embedding (new additions, renamed stocks etc.)
    """
    store = DataStore()
    q = query.strip().upper()
    rows = store.conn.execute(
        """
        SELECT symbol, company_name, sector, industry FROM stocks
        WHERE (
            symbol LIKE ? OR
            company_name LIKE ? OR
            symbol = ?
        )
        AND symbol NOT IN ({})
        ORDER BY
            CASE WHEN symbol = ? THEN 0
                 WHEN symbol LIKE ? THEN 1
                 ELSE 2 END
        LIMIT ?
        """.format(",".join("?" * len(already_found)) if already_found else "''"),
        [f"{q}%", f"%{query}%", q] + list(already_found) + [q, f"{q}%", limit],
    ).fetchall()
    store.close()

    # Return as lightweight objects matching the Stock interface
    class _S:
        def __init__(self, r):
            self.symbol = r["symbol"]
            self.company_name = r["company_name"]
            self.sector = r["sector"]
            self.industry = r["industry"]

    return [_S(r) for r in rows]


def semantic_search(query: str, limit: int = 5) -> list:
    """
    Hybrid search:
    1. SQL LIKE for exact symbol/name matches (always catches renamed stocks)
    2. Semantic embedding similarity for conceptual matches
    Results are merged, deduped, SQL matches ranked first.
    """
    # Step 1: fast SQL exact/prefix match
    sql_results = _sql_fallback_search(query, limit=5, already_found=set())
    found_symbols = {r.symbol for r in sql_results}

    # Step 2: semantic similarity (skip if no embeddings available)
    semantic_results = []
    try:
        if _embeddings_cache is None:
            load_embeddings()

        if _embeddings_cache is not None and len(_embeddings_cache) > 0:
            query_emb = get_embedding(query)
            scores = np.dot(_embeddings_cache, query_emb)
            top_indices = np.argsort(scores)[::-1]

            for idx in top_indices:
                stock = _stocks_cache[idx]
                if stock.symbol not in found_symbols:
                    semantic_results.append(stock)
                    found_symbols.add(stock.symbol)
                if len(sql_results) + len(semantic_results) >= limit:
                    break
    except Exception:
        pass  # Semantic search is best-effort; SQL fallback always works

    return (sql_results + semantic_results)[:limit]


if __name__ == "__main__":
    build_embeddings()
