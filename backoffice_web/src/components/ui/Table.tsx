import React from 'react';

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
            <div className={`flex justify-center items-center p-8 space-x-2 w-full ${className}`}>
                <div className="w-3 h-3 bg-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
                <div className="w-3 h-3 bg-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></div>
                <div className="w-3 h-3 bg-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
            </div>
        );
    }

    if (data.length === 0) {
        return (
            <div className={`p-8 text-center text-slate-400 border border-dashed border-slate-700 rounded-lg ${className}`}>
                {emptyMessage}
            </div>
        );
    }

    return (
        <div className={`overflow-x-auto rounded-lg border border-slate-800 ${className}`}>
            <table className="w-full text-sm text-left">
                <thead className="text-xs text-slate-400 uppercase bg-slate-900/80 border-b border-slate-800">
                    <tr>
                        {columns.map((col, index) => (
                            <th key={col.key || index} scope="col" className="px-6 py-3 font-medium">
                                {col.header}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.map((row, rowIndex) => (
                        <tr
                            key={rowIndex}
                            className="bg-slate-900/20 border-b border-slate-800/50 hover:bg-slate-800/50 transition-colors"
                        >
                            {columns.map((col, colIndex) => (
                                <td key={colIndex} className="px-6 py-4">
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
