export function formatCurrency(amount: number, currency = 'USD'): string {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(amount);
}

export function formatNumber(num: number): string {
    return new Intl.NumberFormat('en-US').format(num);
}

export function formatDate(date: string | Date): string {
    return new Intl.DateTimeFormat('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
    }).format(new Date(date));
}

export function formatDateTime(date: string | Date): string {
    return new Intl.DateTimeFormat('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    }).format(new Date(date));
}

export function formatRelativeTime(date: string | Date): string {
    const now = new Date();
    const then = new Date(date);
    const seconds = Math.floor((now.getTime() - then.getTime()) / 1000);

    if (seconds < 60) return 'hace un momento';
    if (seconds < 3600) return `hace ${Math.floor(seconds / 60)} min`;
    if (seconds < 86400) return `hace ${Math.floor(seconds / 3600)} horas`;
    return `hace ${Math.floor(seconds / 86400)} días`;
}

export function formatPercentage(value: number): string {
    return `${value.toFixed(1)}%`;
}

export function truncateAddress(address: string, chars = 6): string {
    return `${address.slice(0, chars)}...${address.slice(-chars)}`;
}
