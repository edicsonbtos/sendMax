// User Types
export interface User {
    id: number;
    username: string;
    telegram_user_id: string;
    role: 'admin' | 'operator';
    is_active: boolean;
    created_at: string;
}

// Order Types
export interface Order {
    id: number;
    client_id: number;
    operator_id: number;
    amount_usd: number;
    amount_usdt: number;
    status: 'pending' | 'assigned' | 'completed' | 'cancelled';
    profit_real_usd: number;
    created_at: string;
    completed_at?: string;
}

// Metrics Types
export interface RealtimeMetrics {
    orders_completed_today: number;
    volume_usdt_today: number;
    profit_today: number;
    vault_balance: number;
    active_operators: number;
    pending_withdrawals_count: number;
    pending_withdrawals_amount: number;
}

// Vault Types
export interface VaultBalance {
    vault_balance: number;
    total_profit: number;
    total_withdrawals: number;
    currency: string;
    last_updated: string;
}

export interface VaultTransaction {
    id: number;
    transaction_type: 'PROFIT_IN' | 'WITHDRAWAL_OUT' | 'ADJUSTMENT';
    amount: number;
    balance_before: number;
    balance_after: number;
    description: string;
    operator_id?: number;
    order_id?: number;
    withdrawal_id?: number;
    created_at: string;
}

// Operator Types
export interface Operator extends User {
    stats: {
        total_orders: number;
        completed_orders: number;
        total_profit: number;
        commission_earned: number;
        success_rate: number;
    };
}

// Withdrawal Types
export interface Withdrawal {
    id: number;
    operator_id: number;
    amount: number;
    status: 'pending' | 'approved' | 'paid' | 'rejected';
    created_at: string;
    approved_at?: string;
    approved_by?: number;
}

// Activity Log Types
export interface ActivityLog {
    id: number;
    user_id: number;
    user: User;
    action: string;
    resource_type: string;
    resource_id: number;
    ip_address: string;
    metadata: Record<string, any>;
    created_at: string;
}
