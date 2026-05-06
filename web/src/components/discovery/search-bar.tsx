"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, X, TrendingUp, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { StockSearchResult } from "@/lib/types";

export function SearchBar({ compact = false }: { compact?: boolean }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim() || q.length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    try {
      const data = await api.stocks.search(q, 8);
      setResults(data ?? []);
      setOpen(true);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    setActive(-1);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(val), 250);
  };

  const navigate = (symbol: string) => {
    setOpen(false);
    setQuery("");
    setResults([]);
    router.push(`/stock/${symbol}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive(a => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive(a => Math.max(a - 1, -1));
    } else if (e.key === "Enter" && active >= 0) {
      navigate(results[active].symbol);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Global keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  return (
    <div ref={containerRef} className="relative w-full max-w-xl">
      {/* Input */}
      <div className={`flex items-center gap-2 rounded-xl border transition-all duration-200 ${
        compact ? "px-3 py-1.5" : "px-4 py-2.5"
      } ${
        open || query
          ? "border-emerald-700 bg-zinc-900 shadow-lg shadow-emerald-950/30"
          : "border-zinc-700 bg-zinc-900/60 hover:border-zinc-600"
      }`}>
        {loading
          ? <Loader2 className="h-4 w-4 text-zinc-500 animate-spin shrink-0" />
          : <Search className="h-4 w-4 text-zinc-500 shrink-0" />
        }
        <input
          ref={inputRef}
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => query.length >= 2 && setOpen(true)}
          placeholder={compact ? "Search stocks…" : "Search stocks, sectors, companies…"}
          className="flex-1 bg-transparent text-sm text-zinc-200 placeholder:text-zinc-600 outline-none min-w-0"
          aria-label="Stock search"
          autoComplete="off"
        />
        {query
          ? <button onClick={() => { setQuery(""); setResults([]); setOpen(false); }} className="text-zinc-600 hover:text-zinc-400 transition-colors shrink-0">
              <X className="h-4 w-4" />
            </button>
          : !compact && (
              <kbd className="hidden sm:inline-flex items-center gap-1 rounded border border-zinc-700 px-1.5 py-0.5 text-[10px] text-zinc-600 font-mono shrink-0">
                ⌘K
              </kbd>
            )
        }
      </div>

      {/* Dropdown */}
      {open && results.length > 0 && (
        <div className="absolute top-full mt-1.5 w-full z-50 rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl shadow-black/60 overflow-hidden">
          <ul>
            {results.map((r, i) => (
              <li key={r.symbol}>
                <button
                  onClick={() => navigate(r.symbol)}
                  onMouseEnter={() => setActive(i)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors ${
                    i === active ? "bg-zinc-800" : "hover:bg-zinc-900"
                  } ${i > 0 ? "border-t border-zinc-800/60" : ""}`}
                >
                  <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-emerald-950 border border-emerald-900/50 flex items-center justify-center">
                    <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-emerald-400">{r.symbol}</span>
                      {r.sector && (
                        <span className="text-[10px] text-zinc-600 border border-zinc-800 rounded px-1.5 py-0.5 hidden sm:inline">
                          {r.sector}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-zinc-500 truncate">{r.company_name}</p>
                  </div>
                  {r.latest_price != null && (
                    <div className="text-right shrink-0">
                      <div className="text-sm font-medium text-zinc-300">
                        ₹{r.latest_price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </div>
                      {r.change_1d_pct != null && (
                        <div className={`text-[10px] font-medium ${r.change_1d_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                          {r.change_1d_pct >= 0 ? "+" : ""}{r.change_1d_pct.toFixed(2)}%
                        </div>
                      )}
                    </div>
                  )}
                </button>
              </li>
            ))}
          </ul>
          <div className="px-4 py-2 border-t border-zinc-800 text-[10px] text-zinc-700 flex items-center gap-3">
            <span>↑↓ navigate</span><span>↵ open</span><span>esc close</span>
          </div>
        </div>
      )}

      {open && query.length >= 2 && results.length === 0 && !loading && (
        <div className="absolute top-full mt-1.5 w-full z-50 rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl p-6 text-center text-zinc-600 text-sm">
          No stocks found for "<span className="text-zinc-400">{query}</span>"
        </div>
      )}
    </div>
  );
}
