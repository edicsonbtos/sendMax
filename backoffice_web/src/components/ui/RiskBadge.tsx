import React from "react";
import { cn } from "@/lib/cn";

type RiskLevel = "low" | "medium" | "high" | "critical";

type RiskBadgeProps = {
  level: RiskLevel;
  label?: string;
  className?: string;
};

const styles: Record<RiskLevel, string> = {
  low: "bg-emerald-500/15 text-emerald-300 border border-emerald-400/20 shadow-[0_0_15px_rgba(16,185,129,0.05)]",
  medium: "bg-amber-500/15 text-amber-300 border border-amber-400/20 shadow-[0_0_15px_rgba(245,158,11,0.05)]",
  high: "bg-orange-500/15 text-orange-300 border border-orange-400/20 shadow-[0_0_15px_rgba(249,115,22,0.05)]",
  critical: "bg-rose-500/15 text-rose-300 border border-rose-400/20 shadow-[0_0_15px_rgba(244,63,94,0.05)]",
};

export default function RiskBadge({
  level,
  label,
  className,
}: RiskBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider",
        styles[level],
        className
      )}
    >
      <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-current" />
      {label ?? level}
    </span>
  );
}
