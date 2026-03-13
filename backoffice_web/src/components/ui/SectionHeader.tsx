import React from "react";
import { cn } from "@/lib/cn";

type SectionHeaderProps = {
  title: string;
  subtitle?: string;
  rightSlot?: React.ReactNode;
  className?: string;
};

export default function SectionHeader({
  title,
  subtitle,
  rightSlot,
  className,
}: SectionHeaderProps) {
  return (
    <div className={cn("flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between", className)}>
      <div>
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white drop-shadow-sm">
          {title}
        </h1>
        {subtitle ? (
          <p className="mt-1 text-sm sm:text-base text-white/60 font-medium">{subtitle}</p>
        ) : null}
      </div>

      {rightSlot ? <div className="flex items-center gap-3">{rightSlot}</div> : null}
    </div>
  );
}
