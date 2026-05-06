"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import {
  RefreshCw, Play, Trash2, Terminal, GitBranch, Database,
  Activity, Zap, BarChart3, FileText, ChevronDown, ChevronRight,
  CheckCircle, XCircle, Clock, Loader2, Brain, TrendingUp,
  Server, AlertTriangle,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const ADMIN_TOKEN = process.env.NEXT_PUBLIC_ADMIN_TOKEN ?? "niftysage-admin-2025";

function adminFetch(path: string, method = "GET") {
  return fetch(`${API}/api/admin${path}`, {
    method,
    headers: { "x-admin-token": ADMIN_TOKEN },
  }).then(r => r.json());
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { color: string; icon: React.ReactNode }> = {
    running: { color: "text-blue-400 bg-blue-500/10 border-blue-500/20", icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    done: { color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", icon: <CheckCircle className="w-3 h-3" /> },
    error: { color: "text-red-400 bg-red-500/10 border-red-500/20", icon: <XCircle className="w-3 h-3" /> },
    started: { color: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20", icon: <Clock className="w-3 h-3" /> },
  };
  const c = cfg[status] ?? cfg.started;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${c.color}`}>
      {c.icon} {status}
    </span>
  );
}

function ActionButton({
  label, icon: Icon, onClick, loading, color = "indigo", description,
}: {
  label: string; icon: any; onClick: () => void; loading: boolean;
  color?: string; description?: string;
}) {
  const colors: Record<string, string> = {
    indigo: "bg-indigo-600 hover:bg-indigo-500 shadow-indigo-500/20",
    emerald: "bg-emerald-600 hover:bg-emerald-500 shadow-emerald-500/20",
    amber: "bg-amber-600 hover:bg-amber-500 shadow-amber-500/20",
    violet: "bg-violet-600 hover:bg-violet-500 shadow-violet-500/20",
    red: "bg-red-600 hover:bg-red-500 shadow-red-500/20",
    blue: "bg-blue-600 hover:bg-blue-500 shadow-blue-500/20",
  };
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`flex items-start gap-3 p-4 rounded-xl ${colors[color]} shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all text-white text-left w-full`}
    >
      <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Icon className="w-4 h-4" />}
      </div>
      <div>
        <div className="font-semibold text-sm">{label}</div>
        {description && <div className="text-xs opacity-75 mt-0.5">{description}</div>}
      </div>
    </button>
  );
}

function StatCard({ label, value, sub, icon: Icon, color = "indigo" }: {
  label: string; value: string | number; sub?: string; icon: any; color?: string;
}) {
  const colors: Record<string, string> = {
    indigo: "text-indigo-400 bg-indigo-500/10",
    emerald: "text-emerald-400 bg-emerald-500/10",
    amber: "text-amber-400 bg-amber-500/10",
    violet: "text-violet-400 bg-violet-500/10",
  };
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-3.5 h-3.5" />
        </div>
        <span className="text-xs text-zinc-500 uppercase tracking-wider">{label}</span>
      </div>
      <p className="text-2xl font-bold text-white">
        {typeof value === "number" ? value.toLocaleString("en-IN") : value}
      </p>
      {sub && <p className="text-xs text-zinc-500 mt-1">{sub}</p>}
    </div>
  );
}

// ── Main Admin Page ───────────────────────────────────────────────────────────

export default function AdminPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [stats, setStats] = useState<any>(null);
  const [git, setGit] = useState<any>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [logFile, setLogFile] = useState("server_err.log");
  const [availableLogs, setAvailableLogs] = useState<string[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);
  const [activeJobs, setActiveJobs] = useState<Record<string, boolean>>({});
  const [expandedJob, setExpandedJob] = useState<string | null>(null);
  const [jobOutputs, setJobOutputs] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState<"overview" | "pipelines" | "logs" | "git">("overview");

  // Auth guard
  useEffect(() => {
    if (status === "unauthenticated") router.push("/login");
    if (status === "authenticated" && (session?.user as any)?.role !== "admin") router.push("/");
  }, [status, session, router]);

  const refreshStats = useCallback(async () => {
    setLoadingStats(true);
    try {
      const [s, g, j] = await Promise.all([
        adminFetch("/stats"),
        adminFetch("/git"),
        adminFetch("/jobs"),
      ]);
      setStats(s);
      setGit(g);
      setJobs(j);
    } catch { /* offline */ }
    setLoadingStats(false);
  }, []);

  const refreshLogs = useCallback(async () => {
    try {
      const data = await adminFetch(`/logs?log_file=${logFile}&lines=150`);
      setLogs(data.lines ?? []);
      setAvailableLogs(data.available_files ?? []);
    } catch { /* offline */ }
  }, [logFile]);

  useEffect(() => { refreshStats(); }, [refreshStats]);
  useEffect(() => { if (activeTab === "logs") refreshLogs(); }, [activeTab, refreshLogs]);

  // Poll running jobs
  useEffect(() => {
    const interval = setInterval(async () => {
      const running = jobs.filter(j => j.status === "running");
      for (const job of running) {
        const detail = await adminFetch(`/jobs/${job.job_id}`).catch(() => null);
        if (detail) {
          setJobOutputs(prev => ({ ...prev, [job.job_id]: detail }));
          if (detail.status !== "running") {
            setJobs(prev => prev.map(j => j.job_id === job.job_id ? { ...j, status: detail.status } : j));
            setActiveJobs(prev => { const n = { ...prev }; delete n[job.job_id]; return n; });
            refreshStats();
          }
        }
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [jobs, refreshStats]);

  async function runAction(endpoint: string, jobKey: string) {
    setActiveJobs(prev => ({ ...prev, [jobKey]: true }));
    try {
      const result = await adminFetch(`/action/${endpoint}`, "POST");
      if (result.job_id) {
        setJobs(prev => [{ job_id: result.job_id, status: "running", cmd: endpoint, started_at: new Date().toISOString() }, ...prev]);
        setExpandedJob(result.job_id);
      }
      await refreshStats();
    } catch {
      setActiveJobs(prev => { const n = { ...prev }; delete n[jobKey]; return n; });
    }
  }

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
      </div>
    );
  }

  const db = stats?.database ?? {};
  const tc = db.table_counts ?? {};

  const TABS = [
    { id: "overview", label: "Overview", icon: BarChart3 },
    { id: "pipelines", label: "Pipelines", icon: Play },
    { id: "logs", label: "Logs", icon: Terminal },
    { id: "git", label: "Git", icon: GitBranch },
  ] as const;

  return (
    <div className="min-h-screen bg-zinc-950">
      {/* Header */}
      <div className="border-b border-zinc-800 bg-zinc-900/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-amber-500 rounded-lg flex items-center justify-center">
              <Server className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white">Admin Control Panel</h1>
              <p className="text-xs text-zinc-500">Nifty Sage — harshh1307@gmail.com</p>
            </div>
          </div>
          <button
            onClick={refreshStats}
            disabled={loadingStats}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingStats ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {/* Tab nav */}
        <div className="max-w-6xl mx-auto px-6 flex gap-1 pb-0">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-amber-500 text-amber-400"
                  : "border-transparent text-zinc-500 hover:text-zinc-300"
              }`}
            >
              <tab.icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-6 space-y-6">

        {/* OVERVIEW TAB */}
        {activeTab === "overview" && (
          <>
            {/* Running jobs alert */}
            {jobs.filter(j => j.status === "running").length > 0 && (
              <div className="flex items-center gap-3 p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-300">
                <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
                <span className="text-sm font-medium">
                  {jobs.filter(j => j.status === "running").length} job(s) running in background
                </span>
              </div>
            )}

            {/* DB stats grid */}
            <div>
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Database</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatCard label="Stocks" value={tc.stocks ?? 0} icon={TrendingUp} color="indigo" />
                <StatCard label="Price Records" value={tc.prices ?? 0} icon={Activity} color="emerald" />
                <StatCard label="News Articles" value={tc.news ?? 0} icon={FileText} color="violet"
                  sub={db.latest_news_date ? `Latest: ${db.latest_news_date?.slice(0, 10)}` : undefined} />
                <StatCard label="Financials" value={tc.quarterly_financials ?? 0} icon={BarChart3} color="amber" />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
                <StatCard label="Signals" value={tc.signal_decisions ?? 0} icon={Brain} color="violet" />
                <StatCard label="Screener Cache" value={db.screener_cache_entries ?? 0} icon={Database} color="indigo"
                  sub="24h TTL" />
                <StatCard label="Latest Price" value={db.latest_price_date ?? "—"} icon={Clock} color="emerald" />
                <StatCard label="Discovery Cache"
                  value={stats?.discovery_cache?.has_data ? "Active" : "Empty"}
                  icon={Zap}
                  color={stats?.discovery_cache?.has_data ? "emerald" : "amber"}
                  sub={stats?.discovery_cache?.expires_at ? `Expires ${new Date(stats.discovery_cache.expires_at).toLocaleTimeString()}` : undefined}
                />
              </div>
            </div>

            {/* Embeddings */}
            {stats?.embeddings && (
              <div className="p-4 rounded-xl bg-zinc-900 border border-zinc-800">
                <div className="flex items-center gap-2 mb-1">
                  <Brain className="w-4 h-4 text-violet-400" />
                  <span className="text-sm font-medium text-zinc-200">Embeddings File</span>
                </div>
                <p className="text-xs text-zinc-500">
                  {stats.embeddings.size_mb} MB · Last updated: {new Date(stats.embeddings.modified).toLocaleString()}
                </p>
              </div>
            )}

            {/* Fetch log */}
            {stats?.fetch_log?.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Fetch Log</h2>
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-800 text-xs text-zinc-500 uppercase tracking-wider">
                        <th className="text-left px-4 py-2.5">Task</th>
                        <th className="text-left px-4 py-2.5">Last Run</th>
                        <th className="text-left px-4 py-2.5">Status</th>
                        <th className="text-right px-4 py-2.5">Records</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.fetch_log.map((row: any, i: number) => (
                        <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                          <td className="px-4 py-2.5 font-medium text-zinc-200">{row.task_name}</td>
                          <td className="px-4 py-2.5 text-zinc-500 text-xs">
                            {row.last_run ? new Date(row.last_run).toLocaleString() : "—"}
                          </td>
                          <td className="px-4 py-2.5">
                            <StatusBadge status={row.status ?? "unknown"} />
                          </td>
                          <td className="px-4 py-2.5 text-right text-zinc-400">
                            {row.records_fetched?.toLocaleString() ?? "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Recent jobs */}
            {jobs.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Recent Jobs</h2>
                <div className="space-y-2">
                  {jobs.slice(0, 5).map(job => (
                    <div key={job.job_id} className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                      <button
                        onClick={() => setExpandedJob(expandedJob === job.job_id ? null : job.job_id)}
                        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-zinc-800/30"
                      >
                        <StatusBadge status={job.status} />
                        <span className="text-sm text-zinc-300 flex-1">{job.cmd}</span>
                        <span className="text-xs text-zinc-600">{new Date(job.started_at).toLocaleTimeString()}</span>
                        {expandedJob === job.job_id ? <ChevronDown className="w-3.5 h-3.5 text-zinc-600" /> : <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />}
                      </button>
                      {expandedJob === job.job_id && jobOutputs[job.job_id] && (
                        <div className="px-4 pb-3 border-t border-zinc-800/60">
                          <pre className="text-xs text-zinc-400 bg-zinc-950 rounded-lg p-3 mt-2 max-h-48 overflow-y-auto font-mono">
                            {(jobOutputs[job.job_id].output ?? []).slice(-50).join("\n") || "No output yet…"}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* PIPELINES TAB */}
        {activeTab === "pipelines" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Data Refresh</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <ActionButton
                  label="Refresh Prices"
                  icon={TrendingUp}
                  description="Fetch latest OHLCV for all 2,400+ stocks"
                  onClick={() => runAction("refresh-prices", "prices")}
                  loading={!!activeJobs["prices"]}
                  color="indigo"
                />
                <ActionButton
                  label="Refresh Financials"
                  icon={BarChart3}
                  description="Update quarterly P&L, balance sheet, cash flow"
                  onClick={() => runAction("refresh-financials", "financials")}
                  loading={!!activeJobs["financials"]}
                  color="emerald"
                />
                <ActionButton
                  label="Refresh News"
                  icon={FileText}
                  description="Fetch latest market and stock news"
                  onClick={() => runAction("refresh-news", "news")}
                  loading={!!activeJobs["news"]}
                  color="violet"
                />
                <ActionButton
                  label="Rebuild Embeddings"
                  icon={Brain}
                  description="Add embeddings for new/missing stocks (incremental)"
                  onClick={() => runAction("rebuild-embeddings", "embeddings")}
                  loading={!!activeJobs["embeddings"]}
                  color="amber"
                />
              </div>
            </div>

            <div>
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Signal Pipeline</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <ActionButton
                  label="Run Signal Pipeline"
                  icon={Zap}
                  description="Run AI signal generation for today's candidates"
                  onClick={() => runAction("run-signals", "signals")}
                  loading={!!activeJobs["signals"]}
                  color="amber"
                />
                <ActionButton
                  label="Run Full Pipeline"
                  icon={Play}
                  description="Prices → Financials → News → Signals (all in sequence)"
                  onClick={() => runAction("run-full-pipeline", "full")}
                  loading={!!activeJobs["full"]}
                  color="emerald"
                />
              </div>
            </div>

            <div>
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Cache Control</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <ActionButton
                  label="Clear Discovery Cache"
                  icon={Trash2}
                  description="Force-refresh discovery buckets on next page load"
                  onClick={() => runAction("clear-discovery-cache", "cache")}
                  loading={!!activeJobs["cache"]}
                  color="red"
                />
              </div>
            </div>

            {/* Live job output */}
            {jobs.filter(j => j.status === "running").length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Live Output</h2>
                {jobs.filter(j => j.status === "running").map(job => (
                  <div key={job.job_id} className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                    <div className="flex items-center gap-2 px-4 py-2.5 border-b border-zinc-800">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
                      <span className="text-sm text-zinc-300">{job.cmd}</span>
                    </div>
                    <pre className="text-xs text-zinc-400 p-4 max-h-64 overflow-y-auto font-mono bg-zinc-950">
                      {(jobOutputs[job.job_id]?.output ?? []).slice(-60).join("\n") || "Starting…"}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* LOGS TAB */}
        {activeTab === "logs" && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <select
                value={logFile}
                onChange={e => setLogFile(e.target.value)}
                className="px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-zinc-200 text-sm focus:outline-none focus:border-indigo-500"
              >
                {availableLogs.length > 0
                  ? availableLogs.map(f => <option key={f} value={f}>{f}</option>)
                  : <option value="server_err.log">server_err.log</option>
                }
              </select>
              <button
                onClick={refreshLogs}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Refresh
              </button>
            </div>

            <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 font-mono text-xs">
              {logs.length === 0 ? (
                <p className="text-zinc-600 text-center py-8">No log lines to show</p>
              ) : (
                <div className="max-h-[60vh] overflow-y-auto space-y-0.5">
                  {logs.map((line, i) => {
                    const isError = line.includes("[ERROR]") || line.includes("Error") || line.includes("Traceback");
                    const isWarn = line.includes("[WARNING]") || line.includes("WARN");
                    const isInfo = line.includes("[INFO]");
                    return (
                      <div
                        key={i}
                        className={`leading-relaxed ${isError ? "text-red-400" : isWarn ? "text-amber-400" : isInfo ? "text-zinc-400" : "text-zinc-500"}`}
                      >
                        {line}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* GIT TAB */}
        {activeTab === "git" && git && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <GitBranch className="w-4 h-4 text-indigo-400" />
                  <span className="text-sm font-medium text-zinc-200">Current Branch</span>
                </div>
                <p className="text-lg font-bold text-indigo-300">{git.branch || "—"}</p>
                {git.remote && <p className="text-xs text-zinc-600 mt-1 truncate">{git.remote}</p>}
              </div>

              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span className="text-sm font-medium text-zinc-200">Uncommitted Changes</span>
                </div>
                {git.dirty_files?.length > 0 ? (
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {git.dirty_files.map((f: string, i: number) => (
                      <p key={i} className="text-xs font-mono text-amber-300">{f}</p>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-emerald-400">✓ Clean working tree</p>
                )}
              </div>
            </div>

            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <Clock className="w-4 h-4 text-zinc-400" />
                <span className="text-sm font-medium text-zinc-200">Recent Commits</span>
              </div>
              <div className="space-y-2">
                {(git.recent_commits ?? []).map((commit: string, i: number) => {
                  const [hash, ...rest] = commit.split(" ");
                  return (
                    <div key={i} className="flex items-start gap-2.5 py-1.5 border-b border-zinc-800/50 last:border-0">
                      <span className="text-xs font-mono text-indigo-400 flex-shrink-0 mt-0.5">{hash}</span>
                      <span className="text-xs text-zinc-400">{rest.join(" ")}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
