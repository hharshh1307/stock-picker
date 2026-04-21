"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, MessageCircle, TrendingUp, Briefcase, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  {
    title: "Discovery",
    href: "/",
    icon: TrendingUp,
    description: "Explore trending stocks",
  },
  {
    title: "Chat",
    href: "/chat",
    icon: MessageCircle,
    description: "AI stock analyst",
  },
  {
    title: "Portfolio",
    href: "/portfolio",
    icon: Briefcase,
    description: "Your holdings & performance",
  },
  {
    title: "Settings & Plans",
    href: "/settings",
    icon: Settings,
    description: "Risk & frequencies",
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-zinc-800 bg-zinc-900/50 backdrop-blur">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 border-b border-zinc-800 px-6">
          <BarChart3 className="h-6 w-6 text-emerald-500" />
          <span className="text-lg font-semibold">Stock Picker</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-4">
          {navItems.map((item) => {
            const isActive = pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-zinc-800 text-zinc-100"
                    : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-100"
                )}
              >
                <item.icon className="h-5 w-5" />
                <div>
                  <div className="font-medium">{item.title}</div>
                  <div className="text-xs text-zinc-500">{item.description}</div>
                </div>
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="border-t border-zinc-800 p-4">
          <div className="text-xs text-zinc-500">
            <p>Nifty 500 Data</p>
            <p className="mt-1">Powered by AI</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
