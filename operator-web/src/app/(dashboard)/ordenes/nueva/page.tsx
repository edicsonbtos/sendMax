"use client";

import Link from "next/link";
import { useState } from "react";

export default function NuevaOrdenPage() {
    const [origen, setOrigen] = useState("");
    const [destino, setDestino] = useState("");
    const [monto, setMonto] = useState("");
    const [beneficiario, setBeneficiario] = useState("");

    return (
        <div className="p-8 max-w-3xl mx-auto">
            <div className="mb-6">
                <Link href="/ordenes" className="text-[#0052FF] hover:underline text-sm font-medium flex items-center gap-1">
                    ← Volver a Órdenes
                </Link>
            </div>

            <div className="mb-8">
                <h1 className="text-3xl font-black text-gray-900 tracking-tight">Nueva Orden</h1>
                <p className="text-gray-500 mt-1">Crea una nueva solicitud de envío.</p>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
                <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">País Origen</label>
                            <select
                                value={origen}
                                onChange={(e) => setOrigen(e.target.value)}
                                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#0052FF] focus:border-transparent outline-none transition-all bg-white"
                            >
                                <option value="" disabled>Selecciona el origen</option>
                                <option value="PERU">Perú</option>
                                <option value="CHILE">Chile</option>
                                <option value="COLOMBIA">Colombia</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">País Destino</label>
                            <select
                                value={destino}
                                onChange={(e) => setDestino(e.target.value)}
                                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#0052FF] focus:border-transparent outline-none transition-all bg-white"
                            >
                                <option value="" disabled>Selecciona el destino</option>
                                <option value="VENEZUELA">Venezuela</option>
                                <option value="COLOMBIA">Colombia</option>
                            </select>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Monto Origen</label>
                        <div className="relative">
                            <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-gray-500 font-medium">
                                $
                            </span>
                            <input
                                type="number"
                                placeholder="0.00"
                                value={monto}
                                onChange={(e) => setMonto(e.target.value)}
                                className="w-full pl-8 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#0052FF] focus:border-transparent outline-none transition-all"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Datos del Beneficiario</label>
                        <textarea
                            placeholder="Nombre completo, cédula, banco, número de cuenta..."
                            value={beneficiario}
                            onChange={(e) => setBeneficiario(e.target.value)}
                            rows={4}
                            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#0052FF] focus:border-transparent outline-none transition-all resize-none"
                        ></textarea>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Comprobante de Pago</label>
                        <input
                            type="file"
                            accept="image/*,.pdf"
                            className="block w-full text-sm text-gray-500
                            file:mr-4 file:py-2 file:px-4
                            file:rounded-lg file:border-0
                            file:text-sm file:font-semibold
                            file:bg-gray-50 file:text-gray-700
                            hover:file:bg-gray-100 transition-colors"
                        />
                    </div>

                    <div className="pt-4 border-t border-gray-100">
                        <button
                            disabled
                            className="w-full bg-gray-200 text-gray-500 px-6 py-3 rounded-lg font-semibold shadow-inner cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            <span>Crear Orden</span>
                            <span className="text-xs bg-gray-300 px-2 py-0.5 rounded text-gray-600">En desarrollo</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
