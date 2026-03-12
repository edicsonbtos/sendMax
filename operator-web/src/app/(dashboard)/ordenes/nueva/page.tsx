"use client";
import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { safeToFixed } from '@/lib/utils';
import {
    CheckCircle, ChevronRight, ChevronLeft, Upload,
    UserPlus, Search, DollarSign, Globe,
    FileText, UserCheck, CheckCircle2, X
} from "lucide-react";

interface Beneficiary {
    id: number;
    full_name: string;
    payment_method: string;
    account_number: string;
    bank_name?: string;
}

interface Client {
    id: number;
    full_name: string;
    phone: string | null;
    total_orders: number;
}

export default function NuevaOrdenStepperPage() {
    const router = useRouter();
    const [currentStep, setCurrentStep] = useState(1);

    // Global State
    const [loading, setLoading] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    // Step 1: Client Selection
    const [clientSearch, setClientSearch] = useState("");
    const [clientResults, setClientResults] = useState<Client[]>([]);
    const [selectedClient, setSelectedClient] = useState<Client | null>(null);
    const [showCreateClient, setShowCreateClient] = useState(false);
    const [newClientPhone, setNewClientPhone] = useState("");

    // Step 2: Remittance Details
    const [amount, setAmount] = useState("");
    const [destCountry, setDestCountry] = useState("VE");
    const [paymentMethod, setPaymentMethod] = useState("Zelle");
    const [calculatedPayout, setCalculatedPayout] = useState<string | null>(null);

    // Step 3: Beneficiary
    const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>([]);
    const [selectedBeneficiary, setSelectedBeneficiary] = useState<number | null>(null);
    const [notes, setNotes] = useState("");

    // Step 4: Voucher Upload
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);

    const fileInputRef = useRef<HTMLInputElement>(null);

    // ─── Step 1 Logic ───
    useEffect(() => {
        const timer = setTimeout(() => {
            if (clientSearch.length >= 2) {
                api.get(`/api/operators/clients/search?q=${clientSearch}`)
                    .then(res => setClientResults(res.data))
                    .catch(() => setClientResults([]));
            } else {
                setClientResults([]);
            }
        }, 300);
        return () => clearTimeout(timer);
    }, [clientSearch]);

    const handleCreateQuickClient = async () => {
        try {
            const res = await api.post("/api/operators/clients/", {
                full_name: clientSearch,
                phone: newClientPhone
            });
            setSelectedClient(res.data);
            setShowCreateClient(false);
            setClientSearch("");
            setClientResults([]);
            setError("");
        } catch (err: any) {
            setError(err.response?.data?.detail || "Error al crear cliente");
        }
    };

    // ─── Step 2 Logic ───
    useEffect(() => {
        if (amount && Number(amount) > 0) {
            // Placeholder real-time rate calculation
            // Depending on destination, we fake a rate for the UI (until the real endpoint exists)
            const rate = destCountry === "VE" ? 45.2 : 4100; // Fake rate for VE (Bs) or CO (COP)
            setCalculatedPayout((Number(amount) * rate).toFixed(2));
        } else {
            setCalculatedPayout(null);
        }
    }, [amount, destCountry]);

    // ─── Step 3 Logic ───
    useEffect(() => {
        if (currentStep === 3 && beneficiaries.length === 0) {
            setLoading(true);
            api.get("/api/operators/beneficiaries")
                .then(res => setBeneficiaries(res.data?.beneficiaries || []))
                .catch(() => setError("Error cargando contactos"))
                .finally(() => setLoading(false));
        }
    }, [currentStep, beneficiaries.length]);

    // ─── Step 4 Logic ───
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setUploadedFile(e.target.files[0]);
        }
    };

    const handleFinalSubmit = async () => {
        if (!uploadedFile) {
            setError("Debes adjuntar el comprobante de pago para finalizar.");
            return;
        }

        setError("");
        setSubmitting(true);

        try {
            const response = await api.post("/api/operators/orders/create", {
                client_id: selectedClient?.id,
                beneficiary_id: selectedBeneficiary,
                amount_usd: parseFloat(amount),
                payment_method: paymentMethod,
                notes: notes,
            });

            setSuccess("✅ " + (response.data?.message || "Orden creada exitosamente"));

            setTimeout(() => {
                router.push("/ordenes");
            }, 2000);
        } catch (error: any) {
            setError(error.response?.data?.detail || "Error al crear la orden");
            setSubmitting(false);
        }
    };

    // ─── Render functions ───
    const canGoNext = () => {
        if (currentStep === 1) return selectedClient !== null;
        if (currentStep === 2) return Number(amount) > 0 && Number(amount) <= 10000;
        if (currentStep === 3) return selectedBeneficiary !== null;
        return false;
    };

    const nextStep = () => {
        if (canGoNext()) setCurrentStep(s => s + 1);
    };

    const prevStep = () => {
        setCurrentStep(s => Math.max(1, s - 1));
    };

    const steps = [
        { num: 1, title: 'Identificación', icon: Search },
        { num: 2, title: 'Remesa', icon: Globe },
        { num: 3, title: 'Destinatario', icon: UserCheck },
        { num: 4, title: 'Comprobante', icon: CheckCircle2 }
    ];

    const renderStepContent = () => {
        switch (currentStep) {
            case 1:
                return (
                    <div className="space-y-6 animate-fade-in">
                        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-6">
                            <h2 className="text-xl font-semibold text-white mb-2 flex items-center gap-2">
                                <Search className="text-blue-400" />
                                Paso 1: Identificación del Cliente
                            </h2>
                            <p className="text-gray-400 text-sm">
                                Busca o registra al remitente del dinero.
                            </p>
                        </div>

                        {selectedClient ? (
                            <div className="p-6 bg-green-500/10 border border-green-500/30 rounded-xl flex justify-between items-center transition-all">
                                <div>
                                    <p className="text-white font-bold text-lg">{selectedClient.full_name}</p>
                                    <p className="text-green-300 text-sm mt-1">{selectedClient.phone || 'Sin teléfono registrado'}</p>
                                    <p className="text-green-400 text-xs mt-2 font-medium bg-green-500/20 inline-block px-2 py-1 rounded-md">
                                        {selectedClient.total_orders} órdenes previas
                                    </p>
                                </div>
                                <button type="button" onClick={() => setSelectedClient(null)} className="flex items-center gap-2 px-4 py-2 border border-red-500/50 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors">
                                    Cambiar Cliente
                                </button>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <input
                                    type="text"
                                    value={clientSearch}
                                    onChange={(e) => setClientSearch(e.target.value)}
                                    placeholder="Buscar por nombre o DNI..."
                                    className="w-full px-5 py-4 bg-[#ffffff05] border border-[#ffffff14] rounded-xl text-white outline-none focus:border-blue-500 focus:bg-[#ffffff0a] transition-all"
                                />

                                {clientResults.length > 0 && (
                                    <div className="bg-[#ffffff05] rounded-xl border border-[#ffffff14] divide-y divide-[#ffffff0a] max-h-60 overflow-y-auto custom-scrollbar">
                                        {clientResults.map(client => (
                                            <div
                                                key={client.id}
                                                onClick={() => { setSelectedClient(client); setClientSearch(""); setClientResults([]); setShowCreateClient(false); }}
                                                className="p-4 hover:bg-[#ffffff0a] cursor-pointer flex justify-between items-center transition-colors"
                                            >
                                                <div>
                                                    <p className="text-white font-medium">{client.full_name}</p>
                                                    <p className="text-gray-400 text-sm">{client.phone || 'N/A'}</p>
                                                </div>
                                                <ChevronRight className="text-gray-500" />
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {clientSearch.length >= 2 && clientResults.length === 0 && !showCreateClient && (
                                    <button
                                        type="button"
                                        onClick={() => setShowCreateClient(true)}
                                        className="w-full p-6 border-2 border-dashed border-blue-500/30 rounded-xl text-blue-400 hover:bg-blue-500/5 transition-colors flex flex-col items-center justify-center gap-2"
                                    >
                                        <UserPlus size={24} />
                                        <span>Registrar a "{clientSearch}" como nuevo cliente</span>
                                    </button>
                                )}

                                {showCreateClient && (
                                    <div className="p-6 bg-[#ffffff05] border border-blue-500/30 rounded-xl space-y-4 animate-slide-up">
                                        <h3 className="text-white font-medium">Completar Registro Rápido</h3>
                                        <input
                                            type="text"
                                            value={newClientPhone}
                                            onChange={(e) => setNewClientPhone(e.target.value)}
                                            placeholder="Teléfono/Celular (Opcional)"
                                            className="w-full px-4 py-3 bg-[#ffffff08] border border-[#ffffff14] rounded-lg text-white outline-none focus:border-blue-500"
                                        />
                                        <div className="flex gap-3 pt-2">
                                            <button type="button" onClick={handleCreateQuickClient} className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors">
                                                Crear y Continuar
                                            </button>
                                            <button type="button" onClick={() => setShowCreateClient(false)} className="px-6 py-3 border border-white/10 text-gray-300 hover:text-white hover:bg-white/5 rounded-lg font-medium transition-colors">
                                                Cancelar
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                );

            case 2:
                return (
                    <div className="space-y-6 animate-fade-in">
                        <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-6 mb-6">
                            <h2 className="text-xl font-semibold text-white mb-2 flex items-center gap-2">
                                <DollarSign className="text-purple-400" />
                                Paso 2: Detalles de Remesa
                            </h2>
                            <p className="text-gray-400 text-sm">
                                Define el monto a enviar y calcula la conversión en tiempo real.
                            </p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-400">País de Destino</label>
                                <select
                                    value={destCountry}
                                    onChange={(e) => setDestCountry(e.target.value)}
                                    className="w-full px-4 py-4 bg-[#ffffff05] border border-[#ffffff14] rounded-xl text-white outline-none focus:border-purple-500"
                                >
                                    <option value="VE">🇻🇪 Venezuela</option>
                                    <option value="CO">🇨🇴 Colombia</option>
                                    <option value="AR">🇦🇷 Argentina</option>
                                </select>
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-400">Origen de Fondos</label>
                                <select
                                    value={paymentMethod}
                                    onChange={(e) => setPaymentMethod(e.target.value)}
                                    className="w-full px-4 py-4 bg-[#ffffff05] border border-[#ffffff14] rounded-xl text-white outline-none focus:border-purple-500"
                                >
                                    <option value="Zelle">Zelle (USD)</option>
                                    <option value="Cash">Efectivo (USD)</option>
                                </select>
                            </div>
                        </div>

                        <div className="space-y-2 pt-4">
                            <label className="text-sm font-medium text-gray-400">Monto a Enviar (USD)</label>
                            <div className="relative">
                                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-bold">$</span>
                                <input
                                    type="number"
                                    step="0.01"
                                    value={amount}
                                    onChange={(e) => setAmount(e.target.value)}
                                    className="w-full pl-10 pr-4 py-4 bg-[#ffffff05] border border-[#ffffff14] rounded-xl text-white text-2xl font-bold outline-none focus:border-purple-500 transition-colors"
                                    placeholder="0.00"
                                />
                            </div>
                        </div>

                        {calculatedPayout && (
                            <div className="mt-4 p-5 bg-[#ffffff05] border border-purple-500/30 rounded-xl flex justify-between items-center animate-slide-up">
                                <div>
                                    <p className="text-sm text-gray-400">El destinatario recibe aprox:</p>
                                    <p className="text-3xl font-bold text-purple-400 mt-1">
                                        {calculatedPayout} <span className="text-lg">{destCountry === 'VE' ? 'Bs' : 'COP'}</span>
                                    </p>
                                </div>
                                <div className="text-right">
                                    <p className="text-xs text-gray-500">Tasa de cambio calculada</p>
                                    <p className="text-sm font-bold text-gray-300">Tiempo Real ⚡</p>
                                </div>
                            </div>
                        )}
                    </div>
                );

            case 3:
                return (
                    <div className="space-y-6 animate-fade-in">
                        <div className="bg-orange-500/10 border border-orange-500/20 rounded-xl p-6">
                            <h2 className="text-xl font-semibold text-white mb-2 flex items-center gap-2">
                                <UserCheck className="text-orange-400" />
                                Paso 3: Contacto Destino
                            </h2>
                            <p className="text-gray-400 text-sm">
                                Selecciona a quién se le enviará el dinero en {destCountry === 'VE' ? 'Venezuela' : destCountry}.
                            </p>
                        </div>

                        {loading ? (
                            <div className="py-12 flex justify-center"><div className="w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full animate-spin" /></div>
                        ) : beneficiaries.length === 0 ? (
                            <div className="p-6 border-2 border-dashed border-[#ffffff14] rounded-xl text-center">
                                <p className="text-gray-400 mb-4">Aún no tienes destintarios guardados.</p>
                                <button onClick={() => router.push('/clientes/nuevo')} className="px-6 py-2 bg-white/5 hover:bg-white/10 text-white rounded-lg transition-colors">
                                    Añadir Nuevo Beneficiario
                                </button>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 gap-3 max-h-96 overflow-y-auto custom-scrollbar pr-2">
                                {beneficiaries.map((b) => (
                                    <div
                                        key={b.id}
                                        onClick={() => setSelectedBeneficiary(b.id)}
                                        className={`p-5 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between ${selectedBeneficiary === b.id
                                            ? "border-orange-500 bg-orange-500/10"
                                            : "border-[#ffffff14] bg-[#ffffff05] hover:border-[#ffffff2a]"
                                            }`}
                                    >
                                        <div>
                                            <p className="text-white font-medium text-lg">{b.full_name}</p>
                                            <div className="flex gap-2 mt-1">
                                                <span className="text-xs px-2 py-0.5 bg-white/5 rounded text-gray-300 border border-white/10">{b.payment_method}</span>
                                                <span className="text-xs px-2 py-0.5 bg-white/5 rounded text-gray-300 border border-white/10">{b.account_number}</span>
                                            </div>
                                            {b.bank_name && <p className="text-gray-400 text-xs mt-2">{b.bank_name}</p>}
                                        </div>
                                        {selectedBeneficiary === b.id && (
                                            <div className="w-8 h-8 rounded-full bg-orange-500 flex items-center justify-center shadow-[0_0_15px_rgba(249,115,22,0.4)]">
                                                <CheckCircle2 size={18} className="text-white" />
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}

                        <div className="pt-4 border-t border-[#ffffff14]">
                            <label className="text-sm font-medium text-gray-400 mb-2 block">Referencia Adicional (Opcional)</label>
                            <textarea
                                value={notes}
                                onChange={(e) => setNotes(e.target.value)}
                                className="w-full px-4 py-3 bg-[#ffffff05] border border-[#ffffff14] rounded-xl text-white outline-none focus:border-orange-500"
                                placeholder="Notas para Backoffice..."
                                rows={2}
                            />
                        </div>
                    </div>
                );

            case 4:
                return (
                    <div className="space-y-6 animate-fade-in">
                        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-6">
                            <h2 className="text-xl font-semibold text-emerald-400 mb-2 flex items-center gap-2">
                                <Upload size={24} />
                                Paso 4: Evidencia de Pago
                            </h2>
                            <p className="text-gray-400 text-sm">
                                Subir el comprobante de captura para el cierre de la orden. Requisito obligatorio.
                            </p>
                        </div>

                        <div
                            className={`border-2 border-dashed rounded-2xl p-10 flex flex-col items-center justify-center transition-all ${uploadedFile ? 'border-emerald-500 bg-emerald-500/5' : 'border-gray-600 bg-[#ffffff05] hover:border-gray-400 cursor-pointer'
                                }`}
                            onClick={() => !uploadedFile && fileInputRef.current?.click()}
                        >
                            <input
                                type="file"
                                className="hidden"
                                ref={fileInputRef}
                                accept="image/png, image/jpeg, application/pdf"
                                onChange={handleFileChange}
                            />

                            {uploadedFile ? (
                                <div className="text-center animate-slide-up">
                                    <div className="w-16 h-16 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                        <FileText size={32} />
                                    </div>
                                    <p className="text-white font-medium text-lg">{uploadedFile.name}</p>
                                    <p className="text-emerald-400 text-sm mt-1">Archivo preparado para enviarse</p>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); setUploadedFile(null); }}
                                        className="mt-4 px-4 py-1.5 border border-red-500/30 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors text-sm"
                                    >
                                        Quitar archivo
                                    </button>
                                </div>
                            ) : (
                                <div className="text-center text-gray-400">
                                    <Upload size={48} className="mx-auto mb-4 text-gray-500" />
                                    <p className="text-lg font-medium text-white mb-2">Haz clic para buscar tu comprobante</p>
                                    <p className="text-sm">JPG, PNG o PDF garantizan la revisión más rápida.</p>
                                </div>
                            )}
                        </div>

                        {/* Order Summary Recap */}
                        {uploadedFile && (
                            <div className="bg-[#ffffff05] border border-[#ffffff14] rounded-xl p-5 animate-slide-up">
                                <p className="text-sm text-gray-500 uppercase tracking-widest font-bold mb-3 border-b border-[#ffffff14] pb-2">Resumen Final</p>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <p className="text-gray-400 text-xs text-uppercase">Remitente</p>
                                        <p className="text-white font-medium">{selectedClient?.full_name}</p>
                                    </div>
                                    <div>
                                        <p className="text-gray-400 text-xs text-uppercase">Envía</p>
                                        <p className="text-white font-bold">${amount} USD</p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                );
        }
    };

    return (
        <div className="p-4 md:p-8 max-w-4xl mx-auto space-y-6 pt-10">
            {/* Header Steps */}
            <div className="flex justify-between items-center relative mb-12">
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-[#ffffff14] -z-10 rounded-full">
                    <div
                        className="h-full bg-blue-500 transition-all duration-500 ease-out rounded-full"
                        style={{ width: `${((currentStep - 1) / 3) * 100}%` }}
                    />
                </div>

                {steps.map((step) => {
                    const isActive = step.num === currentStep;
                    const isPassed = step.num < currentStep;
                    const Icon = step.icon;
                    return (
                        <div key={step.num} className="flex flex-col items-center">
                            <div className={`w-12 h-12 rounded-full flex items-center justify-center border-4 border-[#0a0f1e] transition-all duration-300 ${isActive ? 'bg-blue-500 text-white scale-110 shadow-[0_0_15px_rgba(59,130,246,0.5)]' :
                                isPassed ? 'bg-blue-400 text-white' :
                                    'bg-[#1e293b] text-gray-500'
                                }`}>
                                {isPassed ? <CheckCircle size={20} /> : <Icon size={isActive ? 20 : 18} />}
                            </div>
                            <span className={`text-xs mt-3 lg:absolute lg:top-14 whitespace-nowrap font-medium transition-colors ${isActive ? 'text-white' : isPassed ? 'text-blue-400' : 'text-gray-600'
                                }`}>
                                {step.title}
                            </span>
                        </div>
                    );
                })}
            </div>

            {/* Error & Success Modals */}
            {error && (
                <div className="p-4 mb-4 border border-red-500/30 bg-red-500/10 text-red-400 rounded-xl flex items-center justify-between animate-shake">
                    <span>{error}</span>
                    <button onClick={() => setError("")} className="hover:text-red-300"><X size={16} /></button>
                </div>
            )}

            {success && (
                <div className="p-6 mb-4 border border-emerald-500/50 bg-emerald-500/10 rounded-xl text-center space-y-2 animate-fade-in shadow-[0_0_20px_rgba(16,185,129,0.1)]">
                    <CheckCircle className="mx-auto text-emerald-400 mb-2" size={32} />
                    <p className="text-emerald-400 font-bold text-lg">{success}</p>
                    <p className="text-white/60 text-sm">Redirigiendo a tus operaciones...</p>
                </div>
            )}

            {/* Main Content Area */}
            <div className={`transition-opacity duration-300 ${submitting || success ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
                {renderStepContent()}
            </div>

            {/* Navigation Footer */}
            <div className="flex justify-between pt-8 border-t border-[#ffffff14] mt-8">
                <button
                    onClick={prevStep}
                    disabled={currentStep === 1 || submitting || success !== ""}
                    className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${currentStep === 1 ? 'opacity-0 pointer-events-none' : 'bg-white/5 hover:bg-white/10 text-white border border-[#ffffff14]'
                        }`}
                >
                    <ChevronLeft size={18} /> Atrás
                </button>

                {currentStep < 4 ? (
                    <button
                        onClick={nextStep}
                        disabled={!canGoNext()}
                        className={`flex items-center gap-2 px-8 py-3 rounded-xl font-medium transition-all ${canGoNext() ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-[0_4px_14px_rgba(37,99,235,0.4)]' : 'bg-gray-800 text-gray-500 cursor-not-allowed'
                            }`}
                    >
                        Siguiente Paso <ChevronRight size={18} />
                    </button>
                ) : (
                    <button
                        onClick={handleFinalSubmit}
                        disabled={!uploadedFile || submitting}
                        className={`flex items-center gap-2 px-8 py-3 rounded-xl font-medium transition-all ${uploadedFile && !submitting ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-[0_4px_14px_rgba(16,185,129,0.4)]' : 'bg-gray-800 text-gray-500 cursor-not-allowed'
                            }`}
                    >
                        {submitting ? (
                            <><div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Procesando...</>
                        ) : (
                            <><CheckCircle size={18} /> Procesar Orden Final</>
                        )}
                    </button>
                )}
            </div>
        </div>
    );
}
