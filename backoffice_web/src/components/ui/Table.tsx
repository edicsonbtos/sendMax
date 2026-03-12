import React from 'react';
import { cn } from '@/lib/utils';

interface Column<T> {
    key: string;
    header: string;
    render?: (row: T) => React.ReactNode;
}

interface TableProps<T> {
    columns: Column<T>[];
    data: T[];
    loading?: boolean;
    emptyMessage?: string;
    className?: string;
}

export default function Table<T extends Record<string, any>>({
    columns,
    data,
    loading = false,
    emptyMessage = 'No hay datos disponibles',
    className = ''
}: TableProps<T>) {
    if (loading) {
        return (
            <div className={cn("flex justify-center items-center p-12 space-x-2 w-full", className)}>
                <div className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
                <div className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></div>
                <div className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
            </div>
        );
    }

    if (data.length === 0) {
        return (
            <div className={cn("p-12 text-center text-gray-500 border border-dashed border-white/10 rounded-2xl bg-white/5", className)}>
                {emptyMessage}
            </div>
        );
    }

    return (
        <div className={cn("overflow-x-auto rounded-2xl border border-white/10 bg-primary-800/20 backdrop-blur-sm shadow-xl", className)}>
            <table className="w-full text-sm text-left">
                <thead className="text-[11px] text-gray-400 uppercase tracking-widest bg-primary-900/50 border-b border-white/10">
                    <tr>
                        {columns.map((col, index) => (
                            <th key={col.key || index} scope="col" className="px-6 py-4 font-bold">
                                {col.header}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                    {data.map((row, rowIndex) => (
                        <tr
                            key={rowIndex}
                            className="hover:bg-white/5 transition-colors group"
                        >
                            {columns.map((col, colIndex) => (
                                <td key={colIndex} className="px-6 py-4 text-gray-300 font-medium group-hover:text-white transition-colors">
                                    {col.render ? col.render(row) : row[col.key]}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

