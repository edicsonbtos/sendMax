import React from "react";
import Card from "@/components/ui/Card";

type EmptyStateProps = {
  title: string;
  description?: string;
  action?: React.ReactNode;
};

export default function EmptyState({
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <Card className="p-8 sm:p-10 text-center animate-fade-in">
      <div className="mx-auto max-w-xl">
        <div className="mx-auto mb-4 h-14 w-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
          <div className="w-6 h-6 rounded-full border-2 border-dashed border-white/20 animate-pulse" />
        </div>
        <h3 className="text-xl font-bold text-white">{title}</h3>
        {description ? (
          <p className="mt-2 text-sm text-white/60 font-medium">{description}</p>
        ) : null}
        {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
      </div>
    </Card>
  );
}
