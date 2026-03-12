import React, { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    title?: string;
    children: React.ReactNode;
    footer?: React.ReactNode;
    maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
}

export default function Modal({
    isOpen,
    onClose,
    title,
    children,
    footer,
    maxWidth = 'md'
}: ModalProps) {
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = 'unset';
        }
        return () => {
            document.body.style.overflow = 'unset';
        };
    }, [isOpen]);

    if (!isOpen) return null;

    const maxWidthClasses = {
        sm: 'max-w-sm',
        md: 'max-w-md',
        lg: 'max-w-lg',
        xl: 'max-w-xl',
        '2xl': 'max-w-2xl',
        full: 'max-w-full m-4',
    };

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-primary-900/80 backdrop-blur-md transition-opacity animate-fade-in"
                onClick={onClose}
                aria-hidden="true"
            />

            {/* Modal panel */}
            <div
                className={cn(
                    "relative w-full shadow-2xl transition-all flex flex-col max-h-[90vh] animate-scale-in",
                    "bg-primary-900 border border-white/10 rounded-3xl overflow-hidden shadow-[0_0_50px_rgba(0,0,0,0.5)]",
                    maxWidthClasses[maxWidth]
                )}
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-white/10">
                    {title ? (
                        <h3 className="text-xl font-bold text-white tracking-tight">
                            {title}
                        </h3>
                    ) : <div />}
                    <button
                        onClick={onClose}
                        className="p-2 text-gray-400 bg-white/5 hover:bg-white/10 hover:text-white rounded-xl transition-all duration-200"
                    >
                        <X size={20} />
                        <span className="sr-only">Cerrar modal</span>
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 overflow-y-auto flex-1 custom-scrollbar">
                    {children}
                </div>

                {/* Footer */}
                {footer && (
                    <div className="flex items-center justify-end p-6 border-t border-white/10 space-x-3 bg-white/5">
                        {footer}
                    </div>
                )}
            </div>
        </div>
    );
}

