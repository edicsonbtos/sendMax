import React from 'react';
import { cn } from '@/lib/utils';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    color?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'default';
    variant?: 'solid' | 'flat' | 'outline';
}

export default function Badge({
    children,
    color = 'primary',
    variant = 'flat',
    className = '',
    ...props
}: BadgeProps) {
    const baseStyle = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider';

    const colors = {
        primary: {
            flat: 'bg-blue-500/10 text-blue-400 border border-blue-500/20',
            solid: 'bg-blue-600 text-white',
            outline: 'bg-transparent border border-blue-500/50 text-blue-400',
        },
        success: {
            flat: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
            solid: 'bg-emerald-500 text-white',
            outline: 'bg-transparent border border-emerald-500/50 text-emerald-400',
        },
        warning: {
            flat: 'bg-amber-500/10 text-amber-500 border border-amber-500/20',
            solid: 'bg-amber-500 text-white',
            outline: 'bg-transparent border border-amber-500/50 text-amber-500',
        },
        danger: {
            flat: 'bg-red-500/10 text-red-500 border border-red-500/20',
            solid: 'bg-red-500 text-white',
            outline: 'bg-transparent border border-red-500/50 text-red-500',
        },
        info: {
            flat: 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20',
            solid: 'bg-cyan-500 text-white',
            outline: 'bg-transparent border border-cyan-500/50 text-cyan-400',
        },
        default: {
            flat: 'bg-white/5 text-gray-400 border border-white/10',
            solid: 'bg-gray-600 text-white',
            outline: 'bg-transparent border border-gray-600 text-gray-400',
        },
    };

    const selectedClass = colors[color][variant];

    return (
        <span className={cn(baseStyle, selectedClass, className)} {...props}>
            {children}
        </span>
    );
}

