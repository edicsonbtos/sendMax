import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export function sleep(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

export function generateId() {
    return Math.random().toString(36).substring(2, 9);
}
