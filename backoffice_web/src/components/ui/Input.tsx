import React from 'react';
import { cn } from '@/lib/cn';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement | HTMLTextAreaElement> {
    label?: string;
    error?: string;
    icon?: React.ReactNode;
    helperText?: string;
    multiline?: boolean;
    rows?: number;
}

export default function Input({ 
    label, 
    error, 
    icon, 
    className = '', 
    multiline,
    rows = 3,
    helperText,
    ...props 
}: InputProps) {
    return (
        <div className={cn("w-full group", className)}>
            {label && (
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 ml-1">
                    {label}
                </label>
            )}
            <div className="relative">
                {icon && (
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-gray-500 group-focus-within:text-blue-400 transition-colors">
                        {icon}
                    </div>
                )}
                {multiline ? (
                    <textarea
                        rows={rows}
                        className={cn(
                            "w-full bg-white/5 border border-white/10 text-white text-sm rounded-xl block p-3 transition-all duration-300",
                            "focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 focus:bg-white/10 outline-none",
                            "placeholder:text-gray-600 resize-none",
                            error ? "border-red-500 focus:ring-red-500/10 focus:border-red-500" : ""
                        )}
                        {...(props as React.TextareaHTMLAttributes<HTMLTextAreaElement>)}
                    />
                ) : (
                    <input
                        className={cn(
                            "w-full bg-white/5 border border-white/10 text-white text-sm rounded-xl block p-3 transition-all duration-300",
                            "focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 focus:bg-white/10 outline-none",
                            "placeholder:text-gray-600",
                            icon ? "pl-12" : "pl-4",
                            error ? "border-red-500 focus:ring-red-500/10 focus:border-red-500" : ""
                        )}
                        {...props}
                    />
                )}
            </div>
            {helperText && !error && <p className="mt-2 text-[10px] text-white/30 font-medium ml-1 uppercase tracking-wider">{helperText}</p>}
            {error && <p className="mt-2 text-xs text-red-500 font-medium ml-1">{error}</p>}
        </div>
    );
}
