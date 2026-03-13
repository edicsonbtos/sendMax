import React from "react";
import { cn } from "@/lib/cn";

type CountryPillProps = {
  country: string;
  className?: string;
};

export default function CountryPill({ country, className }: CountryPillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-lg px-2 py-0.5 text-[11px] font-bold bg-white/5 text-cyan-200 border border-white/10 shadow-sm",
        className
      )}
    >
      {country}
    </span>
  );
}
