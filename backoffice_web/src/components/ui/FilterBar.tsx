import React from "react";
import Card from "@/components/ui/Card";
import { cn } from "@/lib/cn";

type FilterBarProps = {
  children: React.ReactNode;
  className?: string;
};

export default function FilterBar({ children, className }: FilterBarProps) {
  return (
    <Card className={cn("p-4 sm:p-5 border-white/5 bg-white/[0.02] backdrop-blur-md", className)}>
      <div className="flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-center">
        {children}
      </div>
    </Card>
  );
}
