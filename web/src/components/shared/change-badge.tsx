import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface ChangeBadgeProps {
  value: number | null | undefined;
  showIcon?: boolean;
  className?: string;
}

export function ChangeBadge({ value, showIcon = true, className }: ChangeBadgeProps) {
  if (value === null || value === undefined) {
    return <span className={cn("text-zinc-500", className)}>-</span>;
  }

  const isPositive = value > 0;
  const isNegative = value < 0;
  const sign = isPositive ? "+" : "";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 font-medium",
        isPositive && "text-emerald-500",
        isNegative && "text-red-500",
        !isPositive && !isNegative && "text-zinc-400",
        className
      )}
    >
      {showIcon && (
        <>
          {isPositive && <TrendingUp className="h-3.5 w-3.5" />}
          {isNegative && <TrendingDown className="h-3.5 w-3.5" />}
          {!isPositive && !isNegative && <Minus className="h-3.5 w-3.5" />}
        </>
      )}
      {sign}{value.toFixed(1)}%
    </span>
  );
}
