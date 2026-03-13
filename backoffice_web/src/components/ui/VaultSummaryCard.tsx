import React from "react";
import Card from "@/components/ui/Card";
import MoneyCell from "@/components/ui/MoneyCell";
import RiskBadge from "@/components/ui/RiskBadge";

type VaultSummaryCardProps = {
  title: string;
  balance: string | number;
  currency?: string;
  risk?: "low" | "medium" | "high" | "critical";
  subtitle?: string;
};

export default function VaultSummaryCard({
  title,
  balance,
  currency = "USDT",
  risk = "low",
  subtitle,
}: VaultSummaryCardProps) {
  return (
    <Card className="p-5 sm:p-6 group hover:border-white/20 transition-all duration-300">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold text-white/40 uppercase tracking-[0.2em]">{title}</p>
          <div className="mt-4">
            <MoneyCell value={balance} currency={currency} emphasize />
          </div>
          {subtitle ? <p className="mt-2 text-[11px] text-white/30 font-medium">{subtitle}</p> : null}
        </div>
        <div className="z-10">
          <RiskBadge level={risk} />
        </div>
      </div>
    </Card>
  );
}
