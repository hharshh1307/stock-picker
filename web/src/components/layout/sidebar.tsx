"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import type { Session } from "next-auth";
import {
  BarChart3, MessageCircle, TrendingUp, Briefcase,
  Settings, Brain, Shield, LogIn, LogOut, Lock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SearchBar } from "@/components/discovery/search-bar";

// Public — always visible
const PUBLIC_NAV = [
  {
    title: "Discovery",
    href: "/",
    icon: TrendingUp,
    description: "Explore trending stocks",
    requireAuth: false,
  },
];

// Auth-gated — visible only when logged in
const AUTHED_NAV = [
  {
    title: "Chat",
    href: "/chat",
    icon: MessageCircle,
    description: "AI stock analyst",
    requireAuth: true,
  },
  {
    title: "Portfolio",
    href: "/portfolio",
    icon: Briefcase,
    description: "Your holdings & P&L",
    requireAuth: true,
  },
  {
    title: "Signals",
    href: "/signals",
    icon: Brain,
    description: "ML + AI daily picks",
    requireAuth: true,
  },
  {
    title: "Settings",
    href: "/settings",
    icon: Settings,
    description: "Risk & frequencies",
    requireAuth: true,
  },
];

// Admin-only nav
const ADMIN_NAV = [
  {
    title: "Admin Panel",
    href: "/admin",
    icon: Shield,
    description: "Pipelines & system control",
    requireAuth: true,
  },
];

interface SidebarProps {
  session?: Session | null;
}

export function Sidebar({ session }: SidebarProps) {
  const pathname = usePathname();
  const isAuthed = !!session?.user;
  const isAdmin = (session?.user as any)?.role === "admin";
  const userEmail = session?.user?.email ?? "";
  const userName = session?.user?.name ?? userEmail.split("@")[0];

  const visibleNav = [
    ...PUBLIC_NAV,
    ...(isAuthed ? AUTHED_NAV : []),
    ...(isAdmin ? ADMIN_NAV : []),
  ];

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-zinc-800 bg-zinc-900/50 backdrop-blur">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 border-b border-zinc-800 px-6">
          <div className="w-7 h-7 bg-indigo-500 rounded-lg flex items-center justify-center">
            <BarChart3 className="h-4 w-4 text-white" />
          </div>
          <span className="text-lg font-semibold">Nifty Sage</span>
        </div>

        {/* Search */}
        <div className="px-3 py-3 border-b border-zinc-800/60">
          <SearchBar compact />
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-0.5 p-3 overflow-y-auto">
          {visibleNav.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors group",
                  isActive
                    ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/20"
                    : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-100"
                )}
              >
                <item.icon
                  className={cn(
                    "h-4 w-4 flex-shrink-0",
                    isActive ? "text-indigo-400" : "text-zinc-500 group-hover:text-zinc-300"
                  )}
                />
                <div className="min-w-0">
                  <div className="font-medium truncate">{item.title}</div>
                  <div className="text-xs text-zinc-600 truncate">{item.description}</div>
                </div>
                {item.href === "/admin" && (
                  <span className="ml-auto text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded-full font-medium">
                    ADMIN
                  </span>
                )}
              </Link>
            );
          })}

          {/* Locked items preview (when logged out) */}
          {!isAuthed && (
            <div className="mt-3 pt-3 border-t border-zinc-800/60 space-y-0.5">
              <p className="text-[10px] uppercase tracking-wider text-zinc-600 px-3 mb-2">Sign in to unlock</p>
              {AUTHED_NAV.map((item) => (
                <Link
                  key={item.href}
                  href="/login"
                  className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-zinc-600 hover:text-zinc-500 transition-colors group"
                >
                  <item.icon className="h-4 w-4 flex-shrink-0 text-zinc-700" />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium truncate">{item.title}</div>
                  </div>
                  <Lock className="w-3 h-3 text-zinc-700 flex-shrink-0" />
                </Link>
              ))}
            </div>
          )}
        </nav>

        {/* Footer — auth actions */}
        <div className="border-t border-zinc-800 p-3">
          {isAuthed ? (
            <div className="space-y-2">
              {/* User info */}
              <div className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg bg-zinc-800/50">
                <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center flex-shrink-0 text-white text-xs font-bold">
                  {userName.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-zinc-200 truncate">{userName}</p>
                  {isAdmin && (
                    <p className="text-[10px] text-amber-400">Administrator</p>
                  )}
                </div>
              </div>
              {/* Sign out */}
              <button
                onClick={() => signOut({ callbackUrl: "/" })}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign out
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
            >
              <LogIn className="w-4 h-4" />
              Sign in
            </Link>
          )}
        </div>
      </div>
    </aside>
  );
}
