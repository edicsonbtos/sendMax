import React from "react";
import Card from "@/components/ui/Card";

export type TimelineItem = {
  id: string | number;
  title: string;
  description?: string;
  time?: string;
  tone?: "default" | "success" | "warning" | "danger";
};

type TimelineProps = {
  items: TimelineItem[];
  title?: string;
};

const toneMap = {
  default: "bg-cyan-400",
  success: "bg-emerald-400",
  warning: "bg-amber-400",
  danger: "bg-rose-400",
};

export default function Timeline({ items, title = "Timeline" }: TimelineProps) {
  return (
    <Card className="p-5 sm:p-6">
      <h3 className="text-sm font-bold text-white/40 uppercase tracking-widest">{title}</h3>
      <div className="mt-6 space-y-6">
        {items.map((item, idx) => (
          <div key={item.id} className="flex gap-4 group">
            <div className="flex flex-col items-center">
              <span className={`mt-1.5 h-3 w-3 rounded-full ${toneMap[item.tone ?? "default"]} shadow-[0_0_10px_rgba(34,211,238,0.2)]`} />
              {idx !== items.length - 1 && <span className="mt-2 h-full w-px bg-white/10 group-hover:bg-white/20 transition-colors" />}
            </div>
            <div className="pb-4">
              <div className="flex flex-wrap items-center gap-3">
                <p className="font-bold text-white tracking-tight">{item.title}</p>
                {item.time ? <span className="text-[10px] font-bold text-white/25 uppercase tracking-wide">{item.time}</span> : null}
              </div>
              {item.description ? (
                <p className="mt-1.5 text-sm text-white/50 leading-relaxed">{item.description}</p>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
