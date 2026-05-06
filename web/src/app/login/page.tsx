"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Lock, Mail, TrendingUp, BarChart3, Sparkles } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") ?? "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const result = await signIn("credentials", {
      email,
      password,
      redirect: false,
    });

    setLoading(false);

    if (result?.error) {
      setError("Invalid email or password. Please try again.");
    } else {
      router.push(callbackUrl);
      router.refresh();
    }
  }

  return (
    <div className="min-h-screen flex bg-zinc-950">
      {/* Left panel — branding */}
      <div className="hidden lg:flex w-1/2 flex-col justify-between p-12 relative overflow-hidden bg-gradient-to-br from-zinc-900 via-zinc-900 to-zinc-950 border-r border-zinc-800">
        {/* Background glows */}
        <div className="absolute top-0 left-0 w-[600px] h-[600px] bg-indigo-600/10 rounded-full -translate-x-1/2 -translate-y-1/2 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-violet-600/10 rounded-full translate-x-1/2 translate-y-1/2 blur-3xl pointer-events-none" />

        <div className="relative">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-indigo-500 rounded-xl flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight text-white">Nifty Sage</span>
          </div>
          <p className="text-zinc-500 text-sm">AI-powered Indian equity research</p>
        </div>

        <div className="relative space-y-8">
          <div>
            <h1 className="text-4xl font-bold text-white leading-tight mb-4">
              Your personal<br />
              <span className="text-indigo-400">stock research</span><br />
              engine.
            </h1>
            <p className="text-zinc-400 text-lg leading-relaxed max-w-sm">
              2,400+ Nifty stocks. Real-time signals. AI that gives decisive answers, not hedged opinions.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {[
              { icon: BarChart3, label: "Discovery Engine", desc: "8 curated stock buckets, refreshed daily" },
              { icon: Sparkles, label: "AI Chat Agent", desc: "Ask anything — get a direct verdict" },
              { icon: TrendingUp, label: "Signal Pipeline", desc: "ML-powered buy signals with approval flow" },
            ].map(({ icon: Icon, label, desc }) => (
              <div key={label} className="flex items-start gap-3 p-4 rounded-xl bg-zinc-800/50 border border-zinc-700/50">
                <div className="w-8 h-8 bg-indigo-500/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Icon className="w-4 h-4 text-indigo-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-zinc-100">{label}</p>
                  <p className="text-xs text-zinc-500 mt-0.5">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-zinc-600">
          For personal use only. Not financial advice.
        </p>
      </div>

      {/* Right panel — login form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-white">Nifty Sage</span>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-1">Welcome back</h2>
            <p className="text-zinc-400 text-sm">Sign in to access your research dashboard</p>
          </div>

          <div className="space-y-4">
            <button
              onClick={() => {
                setLoading(true);
                signIn("google", { callbackUrl });
              }}
              disabled={loading}
              className="w-full py-3 bg-white hover:bg-zinc-100 text-zinc-900 font-semibold rounded-xl transition-all flex items-center justify-center gap-3 text-sm shadow-lg disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
              )}
              Sign in with Google
            </button>
            
            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center">
                {error}
              </div>
            )}
          </div>

          {/* Discovery preview link */}
          <div className="mt-4 text-center">
            <a href="/" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
              ← Browse Discovery (no login required)
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
