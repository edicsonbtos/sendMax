import React from "react";
import Card from "@/components/ui/Card";
import TrendPill from "@/components/ui/TrendPill";
import { cn } from "@/lib/cn";

type MetricCardProps = {
  label: string;
  value: React.ReactNode;
  trend?: string;
  trendDirection?: "up" | "down" | "neutral";
  hint?: string;
  icon?: React.ReactNode;
  className?: string;
};

export default function MetricCard({
  label,
  value,
  trend,
  trendDirection = "neutral",
  hint,
  icon,
  className,
}: MetricCardProps) {
  return (
    <Card className={cn("p-5 sm:p-6 group hover:border-white/20 transition-all duration-300", className)}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold text-white/40 uppercase tracking-widest">{label}</p>
          <div className="mt-3 text-2xl sm:text-3xl font-black tracking-tight text-white drop-shadow-sm">
            {value}
          </div>
          {hint ? <p className="mt-2 text-[10px] text-white/30 font-medium uppercase tracking-wide">{hint}</p> : null}
        </div>

        {icon ? (
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-cyan-400 group-hover:scale-110 transition-transform duration-300">
            {icon}
          </div>
        ) : null}
      </div>

      {trend ? <TrendPill className="mt-5" value={trend} direction={trendDirection} /> : null}
    </Card>
  );
}
