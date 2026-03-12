import React from 'react';
import { cn } from '@/lib/utils';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
    size?: 'sm' | 'md' | 'lg';
    loading?: boolean;
    icon?: React.ReactNode;
}

export default function Button({
    children,
    className = '',
    variant = 'primary',
    size = 'md',
    loading = false,
    icon,
    ...props
}: ButtonProps) {
    const baseStyle = 'inline-flex items-center justify-center font-semibold rounded-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95';

    const variants = {
        primary: 'bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white shadow-lg shadow-blue-500/25 border border-blue-400/20',
        secondary: 'bg-white/5 hover:bg-white/10 text-white border border-white/10 backdrop-blur-md',
        ghost: 'bg-transparent hover:bg-white/5 text-gray-400 hover:text-white',
        danger: 'bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/20',
        success: 'bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border border-emerald-500/20',
    };

    const sizes = {
        sm: 'text-xs px-3 py-1.5 gap-1.5',
        md: 'text-sm px-5 py-2.5 gap-2',
        lg: 'text-base px-8 py-3.5 gap-2.5',
    };

    return (
        <button
            className={cn(baseStyle, variants[variant], sizes[size], className)}
            disabled={loading || props.disabled}
            {...props}
        >
            {loading ? (
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
            ) : icon ? (
                <span className="flex items-center justify-center">{icon}</span>
            ) : null}
            {children}
        </button>
    );
}

