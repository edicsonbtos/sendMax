import React from "react";
import { cn } from "@/lib/cn";

type TrendDirection = "up" | "down" | "neutral";

type TrendPillProps = {
  value: string;
  direction?: TrendDirection;
  className?: string;
};

const styles: Record<TrendDirection, string> = {
  up: "bg-emerald-500/15 text-emerald-300 border border-emerald-400/20 shadow-[0_0_15px_rgba(16,185,129,0.1)]",
  down: "bg-rose-500/15 text-rose-300 border border-rose-400/20 shadow-[0_0_15px_rgba(244,63,94,0.1)]",
  neutral: "bg-white/10 text-white/70 border border-white/10",
};

export default function TrendPill({
  value,
  direction = "neutral",
  className,
}: TrendPillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold tracking-tight",
        styles[direction],
        className
      )}
    >
      {direction === 'up' && <span className="mr-1">↑</span>}
      {direction === 'down' && <span className="mr-1">↓</span>}
      {value}
    </span>
  );
}
