import React from "react";
import Card from "@/components/ui/Card";
import { cn } from "@/lib/cn";

type StatCardProps = {
  title: string;
  value: React.ReactNode;
  subtitle?: string;
  icon?: React.ReactNode;
  accentClassName?: string;
  className?: string;
};

export default function StatCard({
  title,
  value,
  subtitle,
  icon,
  accentClassName = "from-blue-600/10 to-cyan-500/5",
  className,
}: StatCardProps) {
  return (
    <Card className={cn("relative overflow-hidden p-5 sm:p-6 group", className)}>
      <div className={cn("absolute inset-0 bg-gradient-to-br opacity-40 group-hover:opacity-60 transition-opacity duration-500", accentClassName)} />
      <div className="relative flex items-start justify-between gap-4">
        <div className="z-10">
          <p className="text-[10px] font-bold text-white/50 uppercase tracking-[0.2em]">{title}</p>
          <div className="mt-3 text-2xl sm:text-3xl font-black tracking-tighter text-white">
            {value}
          </div>
          {subtitle ? <p className="mt-2 text-[11px] text-white/40 font-medium">{subtitle}</p> : null}
        </div>

        {icon ? (
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-black/20 text-white/80 group-hover:bg-black/40 transition-all duration-300 z-10">
            {icon}
          </div>
        ) : null}
      </div>
    </Card>
  );
}
