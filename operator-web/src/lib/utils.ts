/**
 * Convierte de forma segura un valor a número con decimales
 * Maneja null, undefined, NaN, strings, etc.
 */
export const safeToFixed = (value: any, decimals: number = 2): string => {
    // Convertir a número
    const num = Number(value);

    // Validar que es un número válido
    if (isNaN(num) || !isFinite(num)) {
        console.warn(`[safeToFixed] Valor inválido recibido:`, value);
        return '0.' + '0'.repeat(decimals);
    }

    return num.toFixed(decimals);
};

/**
 * Formatea números como moneda
 */
export const formatCurrency = (value: any, currency: string = 'USD'): string => {
    const num = Number(value);
    if (isNaN(num)) return `${currency} 0.00`;

    return `${currency} ${num.toFixed(2)}`;
};

/**
 * Formatea porcentajes
 */
export const formatPercent = (value: any, decimals: number = 1): string => {
    const num = Number(value);
    if (isNaN(num)) return '0%';

    return `${num.toFixed(decimals)}%`;
};
