import React from "react";
import { cn } from "@/lib/cn";

type MoneyCellProps = {
  value: string | number;
  currency?: string;
  emphasize?: boolean;
  className?: string;
};

export default function MoneyCell({
  value,
  currency = "USDT",
  emphasize = false,
  className,
}: MoneyCellProps) {
  const formattedValue = typeof value === 'number' 
    ? value.toLocaleString('es-VE', { minimumFractionDigits: 2 })
    : value;

  return (
    <div className={cn("flex items-baseline gap-1.5", className)}>
      <span className={cn("font-bold text-white tracking-tight", emphasize ? "text-xl sm:text-2xl" : "text-sm")}>
        {formattedValue}
      </span>
      <span className={cn("font-bold uppercase tracking-widest text-white/30", emphasize ? "text-xs" : "text-[10px]")}>
        {currency}
      </span>
    </div>
  );
}
