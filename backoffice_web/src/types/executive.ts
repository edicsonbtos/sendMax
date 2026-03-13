import { Severity } from "./common";

export interface ExecutiveRecentOrder {
  public_id: string;
  status: string;
  created_at: string;
  amount_origin: number;
  origin_country: string;
  dest_country: string;
}

export interface ExecutiveLeaderboardItem {
  alias: string;
  full_name?: string;
  trust_score: number;
  rank?: number;
  profit_month?: string;
  orders_month?: number;
}

export interface ExecutiveOverview {
  total_orders: number;
  pending_orders: number;
  completed_orders: number;
  cancelled_orders: number;
  total_volume_usd: number;
  total_profit_usd: number;
  total_profit_real_usd: number;
  status_counts: Record<string, number>;
}

export interface ExecutiveVaultMetrics {
  vault_balance: number;
  total_profit: number;
  total_withdrawals: number;
}

export interface ExecutiveControlCenterData {
  overview: ExecutiveOverview;
  leaderboard: ExecutiveLeaderboardItem[];
  vault: ExecutiveVaultMetrics | null;
  recent_activity: ExecutiveRecentOrder[];
  risk_alerts: {
    stuck_origin_verification_count: number;
    stuck_payment_proof_count: number;
  } | null;
  config: {
    role: string;
    is_admin: boolean;
  };
}

export interface TreasuryBalanceRow {
  origin_country: string;
  fiat_currency: string;
  current_balance: number;
}

export interface TreasuryCountrySummary {
  country: string;
  total_balance_usd: number;
  currencies: TreasuryBalanceRow[];
}

export interface ExecutiveTreasuryData {
  balances: TreasuryBalanceRow[];
  by_country: TreasuryCountrySummary[];
}

export interface ExecutiveVaultRow {
  id: string | number;
  name: string;
  provider?: string;
  type: string;
  balance: number;
  currency: string;
  updated_at?: string;
}

export interface ExecutiveRiskAnomaly {
  public_id: string;
  status: string;
  profit_usdt: number;
}

export interface ExecutiveRiskData {
  stuck_orders: {
    stuck_origin_verification_count: number;
    stuck_payment_proof_count: number;
  };
  pending_withdrawals: {
    count: number;
    amount: number;
  };
  anomalies: ExecutiveRiskAnomaly[];
  integrity: {
    ledger_anomalies: any[];
    stagnant_liquidity: any[];
  };
  health_score: number;
}

export interface ExecutiveAuditEvent {
  date: string;
  type: string;
  detail: string;
  actor: string;
  severity: Severity;
}

export interface ExecutiveAuditData {
  feed: ExecutiveAuditEvent[];
}
