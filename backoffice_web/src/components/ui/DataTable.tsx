import React from "react";
import Card from "@/components/ui/Card";
import { cn } from "@/lib/cn";

export type DataTableColumn<T> = {
  key: string;
  header: React.ReactNode;
  className?: string;
  render: (row: T) => React.ReactNode;
};

type DataTableProps<T> = {
  title?: string;
  subtitle?: string;
  columns: DataTableColumn<T>[];
  data: T[];
  emptyTitle?: string;
  emptyDescription?: string;
  rowKey: (row: T, index: number) => string | number;
  className?: string;
  loading?: boolean;
};

export default function DataTable<T>({
  title,
  subtitle,
  columns,
  data,
  emptyTitle = "No hay datos disponibles",
  emptyDescription = "Ajusta los filtros o espera nuevos registros.",
  rowKey,
  className,
  loading = false,
}: DataTableProps<T>) {
  return (
    <Card className={cn("overflow-hidden border-white/5", className)}>
      {(title || subtitle) && (
        <div className="border-b border-white/5 px-5 py-5 sm:px-6 bg-white/[0.01]">
          {title ? <h3 className="text-lg font-black text-white tracking-tight">{title}</h3> : null}
          {subtitle ? <p className="mt-1 text-sm text-white/40 font-medium">{subtitle}</p> : null}
        </div>
      )}

      {loading ? (
        <div className="px-6 py-20 text-center animate-pulse">
           <div className="mx-auto h-8 w-8 rounded-full border-4 border-white/10 border-t-blue-500 animate-spin mb-4" />
           <p className="text-sm font-bold text-white/40 uppercase tracking-widest">Consultando registros...</p>
        </div>
      ) : data.length === 0 ? (
        <div className="px-6 py-16 text-center">
          <h4 className="text-base font-bold text-white tracking-tight">{emptyTitle}</h4>
          <p className="mt-2 text-sm text-white/40 font-medium">{emptyDescription}</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-white/[0.02]">
                {columns.map((column) => (
                  <th
                    key={column.key}
                    className={cn(
                      "px-5 py-4 text-left text-[10px] font-bold text-white/30 uppercase tracking-[0.2em] sm:px-6",
                      column.className
                    )}
                  >
                    {column.header}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody className="divide-y divide-white/5">
              {data.map((row, index) => (
                <tr key={rowKey(row, index)} className="hover:bg-white/[0.02] transition-colors duration-200">
                  {columns.map((column) => (
                    <td key={column.key} className={cn("px-5 py-4 align-middle sm:px-6", column.className)}>
                      <div className="text-white/80 font-medium tracking-tight">
                        {column.render(row)}
                      </div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
