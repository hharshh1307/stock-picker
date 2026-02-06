"use client";

import { LineChart, Line, ResponsiveContainer } from "recharts";

interface SparklineProps {
  data: number[];
  height?: number;
  className?: string;
}

export function Sparkline({ data, height = 40, className }: SparklineProps) {
  if (!data || data.length === 0) {
    return <div className={`h-[${height}px] ${className}`} />;
  }

  const chartData = data.map((value, index) => ({ value, index }));
  const isPositive = data.length > 1 && data[data.length - 1] >= data[0];
  const strokeColor = isPositive ? "#10b981" : "#ef4444";

  return (
    <div className={className} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line
            type="monotone"
            dataKey="value"
            stroke={strokeColor}
            strokeWidth={1.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
