import React from 'react';

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
    const baseStyle = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';

    const colors = {
        primary: {
            flat: 'bg-cyan-500/10 text-cyan-400',
            solid: 'bg-cyan-500 text-white',
            outline: 'bg-transparent border border-cyan-500/50 text-cyan-400',
        },
        success: {
            flat: 'bg-green-500/10 text-green-400',
            solid: 'bg-green-500 text-white',
            outline: 'bg-transparent border border-green-500/50 text-green-400',
        },
        warning: {
            flat: 'bg-yellow-500/10 text-yellow-500',
            solid: 'bg-yellow-500 text-white',
            outline: 'bg-transparent border border-yellow-500/50 text-yellow-500',
        },
        danger: {
            flat: 'bg-red-500/10 text-red-500',
            solid: 'bg-red-500 text-white',
            outline: 'bg-transparent border border-red-500/50 text-red-500',
        },
        info: {
            flat: 'bg-blue-500/10 text-blue-400',
            solid: 'bg-blue-500 text-white',
            outline: 'bg-transparent border border-blue-500/50 text-blue-400',
        },
        default: {
            flat: 'bg-slate-500/10 text-slate-300',
            solid: 'bg-slate-600 text-white',
            outline: 'bg-transparent border border-slate-600 text-slate-300',
        },
    };

    const selectedClass = colors[color][variant];

    return (
        <span className={`${baseStyle} ${selectedClass} ${className}`} {...props}>
            {children}
        </span>
    );
}
