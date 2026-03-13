export type ApiEnvelope<T> = {
  ok: boolean;
  data: T;
  meta?: Record<string, unknown>;
  timestamp?: string;
};

export type Severity = "INFO" | "WARNING" | "CRITICAL" | "SUCCESS";

export type Status = "pending" | "assigned" | "completed" | "cancelled" | "CREADA" | "ORIGEN_VERIFICANDO" | "ORIGEN_CONFIRMADO" | "EN_PROCESO" | "PAGADA" | "CANCELADA";

export interface CountryPillProps {
  country: string;
  className?: string;
}

export interface MoneyCellProps {
  value: number | string;
  currency?: string;
  className?: string;
}
