import React from "react";
import Card from "@/components/ui/Card";

type LoadingStateProps = {
  title?: string;
  lines?: number;
};

export default function LoadingState({
  title = "Cargando información",
  lines = 4,
}: LoadingStateProps) {
  return (
    <Card className="p-6 overflow-hidden">
      <div className="animate-pulse">
        <div className="h-6 w-56 rounded bg-white/10" />
        <p className="mt-3 text-sm text-white/50">{title}</p>
        <div className="mt-6 space-y-3">
          {Array.from({ length: lines }).map((_, i) => (
            <div key={i} className="h-12 rounded-xl bg-white/5 border border-white/5" />
          ))}
        </div>
      </div>
    </Card>
  );
}
