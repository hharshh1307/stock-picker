"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { StockSearchResult } from "@/lib/types";

export function DiscoverySearch() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<StockSearchResult[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const fetchSuggestions = async () => {
      if (query.trim().length < 3) {
        setSuggestions([]);
        return;
      }
      
      setIsLoading(true);
      try {
        const results = await api.stocks.search(query, 5);
        setSuggestions(results);
      } catch (err) {
        console.error("Failed to search", err);
      } finally {
        setIsLoading(false);
      }
    };

    const debounce = setTimeout(fetchSuggestions, 300);
    return () => clearTimeout(debounce);
  }, [query]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      setShowSuggestions(false);
      router.push(`/stock/${query.trim().toUpperCase()}`);
    }
  };

  const handleSelect = (symbol: string) => {
    setQuery(symbol);
    setShowSuggestions(false);
    router.push(`/stock/${symbol}`);
  };

  return (
    <div ref={wrapperRef} className="relative w-full max-w-md z-50">
      <form onSubmit={handleSearch} className="relative flex items-center">
        <Search className="absolute left-3 h-4 w-4 text-zinc-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setShowSuggestions(true);
          }}
          onFocus={() => setShowSuggestions(true)}
          placeholder="Search stock symbol (e.g., RELIANCE)..."
          className="w-full bg-zinc-900 border border-zinc-800 rounded-full pl-10 pr-24 py-2.5 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all"
        />
        <div className="absolute right-1.5 flex items-center gap-2">
          {isLoading && <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />}
          <button
            type="submit"
            disabled={!query.trim()}
            className="px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 disabled:bg-zinc-800 disabled:text-zinc-500 text-white text-xs font-medium rounded-full transition-colors"
          >
            Search
          </button>
        </div>
      </form>

      {showSuggestions && query.trim() && suggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-zinc-900 border border-zinc-800 rounded-xl overflow-y-auto max-h-[300px] shadow-xl">
          {suggestions.map((stock) => (
            <button
              key={stock.symbol}
              type="button"
              onClick={() => handleSelect(stock.symbol)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-zinc-800 transition-colors border-b border-zinc-800/50 last:border-0 text-left"
            >
              <div>
                <div className="font-medium text-emerald-400">{stock.symbol}</div>
                <div className="text-xs text-zinc-400 truncate max-w-[200px]">{stock.company_name}</div>
              </div>
              <div className="text-xs text-zinc-500 bg-zinc-800 px-2 py-1 rounded">
                {stock.sector || "Unknown"}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
