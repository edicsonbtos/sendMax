export const safeToFixed = (value: any, decimals: number = 2) => {
    if (typeof value !== 'number' || isNaN(value)) {
        console.warn('Valor no es un número:', value);
        return '0.00'; // Valor por defecto
    }
    return value.toFixed(decimals);
};
