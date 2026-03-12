import React from 'react';
import { cn } from '@/lib/utils';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    hover?: boolean;
}

export default function Card({ children, className = '', hover = false, ...props }: CardProps) {
    return (
        <div
            className={cn(
                "bg-primary-800/30 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden",
                hover && "transition-all duration-300 hover:border-blue-500/50 hover:bg-primary-800/50 hover:shadow-[0_0_30px_rgba(37,99,235,0.1)] hover:-translate-y-1",
                className
            )}
            {...props}
        >
            {children}
        </div>
    );
}

