"use client";

import { useEffect, useState, useCallback } from "react";
import { Brain, TrendingUp, TrendingDown, Minus, RefreshCw, CheckCircle, XCircle, Clock, BarChart3, ChevronDown, ChevronUp, Play } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const FREQUENCIES = ["Daily", "Weekly", "Monthly", "Yearly", "Long-term"];

const FREQ_HOLDING: Record<string, string> = {
  Daily: "1 day", Weekly: "1 week", Monthly: "1 month",
  Yearly: "1 year", "Long-term": "1 year+",
};

// ── Types ─────────────────────────────────────────────────────────────────────

interface Signal {
  id: number;
  symbol: string;
  company_name: string;
  sector: string | null;
  ml_rank: number;
  ml_score_1m: number | null;
  ml_outperform_prob: number | null;
  predicted_return_1m_pct: number | null;
  ai_recommendation: "BUY" | "HOLD" | "SKIP";
  ai_confidence: number;
  ai_reasoning: string;
  user_action: "PENDING" | "APPROVED" | "REJECTED" | "SKIPPED";
  user_notes: string | null;
  actioned_at: string | null;
  latest_price: number | null;
}

interface TodaySignals {
  date: string;
  has_signals: boolean;
  signals: Record<string, Signal[]>;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function recColor(r: string) {
  if (r === "BUY")  return "text-emerald-400 bg-emerald-500/10 border-emerald-800";
  if (r === "HOLD") return "text-amber-400 bg-amber-500/10 border-amber-800";
  return "text-zinc-400 bg-zinc-800/60 border-zinc-700";
}

function actionColor(a: string) {
  if (a === "APPROVED") return "text-emerald-400";
  if (a === "REJECTED") return "text-red-400";
  if (a === "SKIPPED")  return "text-zinc-500";
  return "text-amber-400"; // PENDING
}

function probBar(prob: number | null) {
  if (prob == null) return null;
  const pct = Math.round(prob * 100);
  const color = pct >= 60 ? "bg-emerald-500" : pct >= 45 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 bg-zinc-800 rounded-full h-1.5">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] text-zinc-400 w-8 text-right">{pct}%</span>
    </div>
  );
}

// ── Signal Card ───────────────────────────────────────────────────────────────

function SignalCard({ signal, onAction }: {
  signal: Signal;
  onAction: (id: number, action: string, notes?: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [acting, setActing] = useState(false);
  const [notes, setNotes] = useState("");

  const act = async (action: string) => {
    setActing(true);
    await onAction(signal.id, action, notes || undefined);
    setActing(false);
  };

  const isPending = signal.user_action === "PENDING";

  return (
    <div className={`rounded-xl border transition-colors ${
      signal.user_action === "APPROVED" ? "border-emerald-800/60 bg-emerald-950/20" :
      signal.user_action === "REJECTED" ? "border-red-900/40 bg-red-950/10" :
      "border-zinc-800 bg-zinc-900/40"
    }`}>
      {/* Header row */}
      <div className="px-4 py-3 flex items-center gap-3 flex-wrap">
        {/* Rank badge */}
        <span className="text-xs font-mono text-zinc-600 w-5 text-center">#{signal.ml_rank}</span>

        {/* Symbol + company */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-bold text-emerald-400 text-sm">{signal.symbol}</span>
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${recColor(signal.ai_recommendation)}`}>
              {signal.ai_recommendation}
            </span>
            <span className={`text-[10px] font-medium ${actionColor(signal.user_action)}`}>
              {signal.user_action === "PENDING" ? "awaiting your call" : signal.user_action.toLowerCase()}
            </span>
          </div>
          <div className="text-xs text-zinc-500 truncate">{signal.company_name}</div>
        </div>

        {/* Price */}
        {signal.latest_price && (
          <span className="text-sm font-medium text-zinc-300">
            ₹{signal.latest_price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </span>
        )}

        {/* AI confidence */}
        <div className="text-right hidden sm:block">
          <div className="text-xs text-zinc-500">AI conf.</div>
          <div className="text-sm font-medium text-zinc-200">{Math.round(signal.ai_confidence * 100)}%</div>
        </div>

        {/* Expand toggle */}
        <button onClick={() => setExpanded(!expanded)} className="text-zinc-600 hover:text-zinc-400 transition-colors">
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {/* Outperform probability bar */}
      <div className="px-4 pb-2">
        <div className="text-[10px] text-zinc-600 mb-0.5">Outperform Nifty 500 prob.</div>
        {probBar(signal.ml_outperform_prob)}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-zinc-800/60 space-y-4">
          {/* AI reasoning */}
          <div className="rounded-lg bg-zinc-800/40 p-3">
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1 flex items-center gap-1">
              <Brain className="h-3 w-3" /> AI reasoning
            </div>
            <p className="text-sm text-zinc-300 leading-relaxed">{signal.ai_reasoning}</p>
          </div>

          {/* ML stats */}
          <div className="grid grid-cols-3 gap-3 text-center">
            {[
              { label: "ML Score (1m)", value: signal.ml_score_1m != null ? `${signal.ml_score_1m.toFixed(0)}/100` : "—" },
              { label: "Predicted return", value: signal.predicted_return_1m_pct != null ? `${signal.predicted_return_1m_pct > 0 ? "+" : ""}${signal.predicted_return_1m_pct.toFixed(2)}%` : "—" },
              { label: "Sector", value: signal.sector || "—" },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg bg-zinc-800/40 p-2">
                <div className="text-[10px] text-zinc-500">{label}</div>
                <div className="text-xs font-medium text-zinc-200 mt-0.5">{value}</div>
              </div>
            ))}
          </div>

          {/* Action buttons */}
          {isPending && (
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Optional notes..."
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-xs text-zinc-300 placeholder:text-zinc-700 focus:outline-none focus:border-zinc-600"
                value={notes}
                onChange={e => setNotes(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => act("APPROVED")}
                  disabled={acting}
                  className="flex-1 flex items-center justify-center gap-1.5 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-white text-xs font-semibold py-2 rounded-lg transition-colors"
                >
                  <CheckCircle className="h-3.5 w-3.5" /> Approve
                </button>
                <button
                  onClick={() => act("REJECTED")}
                  disabled={acting}
                  className="flex-1 flex items-center justify-center gap-1.5 bg-zinc-800 hover:bg-red-900/40 border border-zinc-700 hover:border-red-800 disabled:opacity-50 text-zinc-300 hover:text-red-400 text-xs font-semibold py-2 rounded-lg transition-colors"
                >
                  <XCircle className="h-3.5 w-3.5" /> Reject
                </button>
                <button
                  onClick={() => act("SKIPPED")}
                  disabled={acting}
                  className="flex items-center justify-center gap-1.5 bg-zinc-800 border border-zinc-700 disabled:opacity-50 text-zinc-500 text-xs py-2 px-3 rounded-lg transition-colors hover:text-zinc-300"
                >
                  <Minus className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}

          {!isPending && (
            <div className={`text-xs font-medium ${actionColor(signal.user_action)}`}>
              {signal.user_action} {signal.actioned_at ? `· ${new Date(signal.actioned_at).toLocaleTimeString()}` : ""}
              {signal.user_notes && <span className="text-zinc-500 ml-2">— {signal.user_notes}</span>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function SignalsPage() {
  const [data, setData] = useState<TodaySignals | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [activeFreq, setActiveFreq] = useState("Monthly");
  const [error, setError] = useState<string | null>(null);

  const fetchSignals = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch(`${API}/api/signals/today`);
      if (!res.ok) throw new Error(`${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError("Could not load signals. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSignals(); }, [fetchSignals]);

  const triggerPipeline = async () => {
    setRunning(true);
    try {
      await fetch(`${API}/api/signals/run`, { method: "POST" });
      // Poll for results after a short delay
      setTimeout(() => { fetchSignals(); setRunning(false); }, 3000);
    } catch { setRunning(false); }
  };

  const handleAction = async (id: number, action: string, notes?: string) => {
    await fetch(`${API}/api/signals/${id}/action`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_action: action, user_notes: notes }),
    });
    await fetchSignals();
  };

  const signals = data?.signals ?? {};
  const freqSignals = signals[activeFreq] ?? [];
  const pendingCount = freqSignals.filter(s => s.user_action === "PENDING").length;
  const buyCount = freqSignals.filter(s => s.ai_recommendation === "BUY").length;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-zinc-500 text-sm">Loading signals…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Brain className="h-7 w-7 text-emerald-500" />
            Daily Signals
          </h1>
          <p className="text-zinc-500 mt-1 text-sm">
            ML retrieval → AI analysis → your decision · {data?.date ?? "today"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchSignals}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-zinc-700 text-sm text-zinc-400 hover:text-zinc-200 hover:border-zinc-500 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={triggerPipeline}
            disabled={running}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-white text-sm font-medium transition-colors"
          >
            <Play className={`h-4 w-4 ${running ? "animate-pulse" : ""}`} />
            {running ? "Running…" : "Run Pipeline"}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-900 bg-red-950/40 px-5 py-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {!data?.has_signals && !error && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-12 text-center">
          <Brain className="h-10 w-10 text-zinc-700 mx-auto mb-4" />
          <p className="text-zinc-500 text-sm mb-4">No signals generated yet for today.</p>
          <p className="text-zinc-600 text-xs">
            Train the ML model first, then click <strong className="text-zinc-400">Run Pipeline</strong>.
          </p>
          <p className="text-zinc-700 text-xs mt-2 font-mono">
            uv run python -c "from ml_pipeline import train_models; train_models()"
          </p>
        </div>
      )}

      {data?.has_signals && (
        <>
          {/* Frequency tabs */}
          <div className="flex gap-1 p-1 bg-zinc-900 border border-zinc-800 rounded-xl w-fit">
            {FREQUENCIES.map(f => {
              const cnt = signals[f]?.length ?? 0;
              const pending = signals[f]?.filter(s => s.user_action === "PENDING").length ?? 0;
              return (
                <button
                  key={f}
                  onClick={() => setActiveFreq(f)}
                  className={`relative px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeFreq === f
                      ? "bg-zinc-700 text-zinc-100"
                      : "text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  {f}
                  {cnt > 0 && (
                    <span className="ml-1.5 text-xs text-zinc-500">({cnt})</span>
                  )}
                  {pending > 0 && (
                    <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-amber-500" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Stats bar */}
          <div className="flex items-center gap-6 text-sm flex-wrap">
            <div className="flex items-center gap-2 text-zinc-500">
              <BarChart3 className="h-4 w-4" />
              <span>Hold: <strong className="text-zinc-200">{FREQ_HOLDING[activeFreq]}</strong></span>
            </div>
            <div className="flex items-center gap-2 text-emerald-500">
              <TrendingUp className="h-4 w-4" />
              <span><strong>{buyCount}</strong> BUY signals</span>
            </div>
            <div className="flex items-center gap-2 text-amber-500">
              <Clock className="h-4 w-4" />
              <span><strong>{pendingCount}</strong> awaiting your review</span>
            </div>
          </div>

          {/* Signal cards */}
          <div className="space-y-3">
            {freqSignals.length === 0 ? (
              <div className="rounded-xl border border-zinc-800 p-8 text-center text-zinc-600 text-sm">
                No signals for {activeFreq} frequency today.
              </div>
            ) : (
              freqSignals.map(signal => (
                <SignalCard
                  key={signal.id}
                  signal={signal}
                  onAction={handleAction}
                />
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
