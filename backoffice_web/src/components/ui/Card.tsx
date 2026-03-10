import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    hover?: boolean;
}

export default function Card({ children, className = '', hover = false, ...props }: CardProps) {
    return (
        <div
            className={`bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl overflow-hidden ${hover ? 'transition-all duration-300 hover:border-cyan-500/50 hover:bg-slate-900/80 hover:shadow-[0_0_20px_rgba(6,182,212,0.15)]' : ''
                } ${className}`}
            {...props}
        >
            {children}
        </div>
    );
}
