import React from "react";
import Card from "@/components/ui/Card";

export type AuditFeedItem = {
  id: string | number;
  actor: string;
  action: string;
  target?: string;
  time?: string;
};

type AuditFeedProps = {
  items: AuditFeedItem[];
  title?: string;
};

export default function AuditFeed({
  items,
  title = "Actividad reciente",
}: AuditFeedProps) {
  return (
    <Card className="p-5 sm:p-6">
      <h3 className="text-sm font-bold text-white/40 uppercase tracking-widest">{title}</h3>
      <div className="mt-6 space-y-3">
        {items.map((item) => (
          <div key={item.id} className="rounded-2xl border border-white/5 bg-white/[0.01] p-4 hover:bg-white/[0.03] transition-colors">
            <p className="text-sm text-white/80 leading-relaxed">
              <span className="font-bold text-white">{item.actor}</span>{" "}
              <span className="text-white/60">{item.action}</span>
              {item.target ? <span className="text-cyan-400 font-medium"> {item.target}</span> : null}
            </p>
            {item.time ? <p className="mt-2 text-[10px] font-bold text-white/20 uppercase tracking-widest">{item.time}</p> : null}
          </div>
        ))}
      </div>
    </Card>
  );
}
