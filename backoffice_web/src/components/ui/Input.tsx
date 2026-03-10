import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
    icon?: React.ReactNode;
}

export default function Input({ label, error, icon, className = '', ...props }: InputProps) {
    return (
        <div className={`w-full ${className}`}>
            {label && <label className="block text-sm font-medium text-slate-300 mb-1.5">{label}</label>}
            <div className="relative">
                {icon && (
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                        {icon}
                    </div>
                )}
                <input
                    className={`w-full bg-slate-900/50 border border-slate-700 text-slate-100 text-sm rounded-lg focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500 block ${icon ? 'pl-10' : 'pl-4'
                        } p-2.5 transition-all duration-200 ${error ? 'border-red-500 focus:ring-red-500/50' : ''}`}
                    {...props}
                />
            </div>
            {error && <p className="mt-1.5 text-xs text-red-500">{error}</p>}
        </div>
    );
}
