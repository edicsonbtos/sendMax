'use client';

import { useState, useEffect } from 'react';
import {
    Users,
    Plus,
    Search,
    Phone,
    MapPin,
    CreditCard,
    ChevronRight,
    X,
    Check
} from 'lucide-react';

interface PaymentMethod {
    id: number;
    country: string;
    bank_name: string;
    account_number: string;
    alias: string;
}

interface Client {
    id: number;
    name: string;
    phone: string;
    payment_methods: PaymentMethod[];
}

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://sendmax11-production.up.railway.app";

const COUNTRIES = [
    { code: 'VENEZUELA', flag: '🇻🇪', name: 'Venezuela' },
    { code: 'COLOMBIA', flag: '🇨🇴', name: 'Colombia' },
    { code: 'ARGENTINA', flag: '🇦🇷', name: 'Argentina' },
    { code: 'CHILE', flag: '🇨🇱', name: 'Chile' },
    { code: 'PERU', flag: '🇵🇪', name: 'Perú' },
    { code: 'MEXICO', flag: '🇲🇽', name: 'México' },
    { code: 'ECUADOR', flag: '🇪🇨', name: 'Ecuador' },
];

export default function ClientesPage() {
    const [clients, setClients] = useState<Client[]>([]);
    const [showModal, setShowModal] = useState(false);
    const [showPaymentModal, setShowPaymentModal] = useState(false);
    const [selectedClient, setSelectedClient] = useState<Client | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [loading, setLoading] = useState(true);

    // Form states
    const [newClient, setNewClient] = useState({ name: '', phone: '' });
    const [newPayment, setNewPayment] = useState({
        country: '',
        bank_name: '',
        account_number: '',
        alias: ''
    });

    useEffect(() => {
        fetchClients();
    }, []);

    const fetchClients = async () => {
        try {
            const res = await fetch(`${apiUrl}/api/operators/beneficiaries`);
            const data = await res.json();
            // Agrupar por cliente
            const grouped = groupByClient(data);
            setClients(grouped);
        } catch (err) {
            console.error('Error:', err);
        } finally {
            setLoading(false);
        }
    };

    const groupByClient = (beneficiaries: any[]) => {
        const map = new Map<string, Client>();
        beneficiaries.forEach(b => {
            const key = b.phone || b.alias;
            if (map.has(key)) {
                map.get(key)!.payment_methods.push({
                    id: b.id,
                    country: b.dest_country,
                    bank_name: b.bank_name || '',
                    account_number: b.account_number || '',
                    alias: b.alias
                });
            } else {
                map.set(key, {
                    id: b.id,
                    name: b.full_name || b.alias,
                    phone: b.phone || '',
                    payment_methods: [{
                        id: b.id,
                        country: b.dest_country,
                        bank_name: b.bank_name || '',
                        account_number: b.account_number || '',
                        alias: b.alias
                    }]
                });
            }
        });
        return Array.from(map.values());
    };

    const handleAddClient = async () => {
        if (!newClient.name || !newClient.phone) return;

        try {
            await fetch(`${apiUrl}/api/operators/beneficiaries`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    alias: newClient.name,
                    full_name: newClient.name,
                    phone: newClient.phone,
                    dest_country: 'PENDING'
                })
            });
            setShowModal(false);
            setNewClient({ name: '', phone: '' });
            fetchClients();
        } catch (err) {
            console.error('Error:', err);
        }
    };

    const handleAddPayment = async () => {
        if (!selectedClient || !newPayment.country) return;

        try {
            await fetch(`${apiUrl}/api/operators/beneficiaries`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    alias: `${selectedClient.name} - ${newPayment.country}`,
                    full_name: selectedClient.name,
                    phone: selectedClient.phone,
                    dest_country: newPayment.country,
                    bank_name: newPayment.bank_name,
                    account_number: newPayment.account_number
                })
            });
            setShowPaymentModal(false);
            setNewPayment({ country: '', bank_name: '', account_number: '', alias: '' });
            fetchClients();
        } catch (err) {
            console.error('Error:', err);
        }
    };

    const filteredClients = clients.filter(c =>
        c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.phone.includes(searchTerm)
    );

    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Mis Contactos</h1>
                    <p className="text-gray-400">{clients.length} contactos guardados</p>
                </div>
                <button
                    onClick={() => setShowModal(true)}
                    className="btn-primary flex items-center gap-2"
                >
                    <Plus className="w-5 h-5" />
                    Nuevo Contacto
                </button>
            </div>

            {/* Búsqueda */}
            <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                    type="text"
                    placeholder="Buscar por nombre o teléfono..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="input-glass pl-12 w-full max-w-md"
                />
            </div>

            {/* Lista de Clientes */}
            <div className="grid gap-4">
                {loading ? (
                    <div className="text-center py-12">
                        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                        <p className="text-gray-400">Cargando contactos...</p>
                    </div>
                ) : filteredClients.length === 0 ? (
                    <div className="card-glass p-12 text-center">
                        <Users className="w-16 h-16 text-gray-500 mx-auto mb-4" />
                        <h3 className="text-xl font-bold text-white mb-2">Sin contactos</h3>
                        <p className="text-gray-400 mb-6">Agrega tu primer contacto para comenzar</p>
                        <button onClick={() => setShowModal(true)} className="btn-primary">
                            <Plus className="w-5 h-5 inline mr-2" />
                            Agregar Contacto
                        </button>
                    </div>
                ) : (
                    filteredClients.map((client) => (
                        <div key={client.id} className="card-glass p-6">
                            <div className="flex items-start justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white text-xl font-bold">
                                        {client.name.charAt(0)}
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-bold text-white">{client.name}</h3>
                                        <p className="text-gray-400 flex items-center gap-2">
                                            <Phone className="w-4 h-4" />
                                            {client.phone || 'Sin teléfono'}
                                        </p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => {
                                        setSelectedClient(client);
                                        setShowPaymentModal(true);
                                    }}
                                    className="btn-secondary text-sm py-2 px-4 flex items-center gap-2"
                                >
                                    <Plus className="w-4 h-4" />
                                    Agregar Destino
                                </button>
                            </div>

                            {/* Métodos de pago/destinos */}
                            {client.payment_methods.length > 0 && (
                                <div className="mt-4 pt-4 border-t border-white/10">
                                    <p className="text-sm text-gray-400 mb-3">Destinos configurados:</p>
                                    <div className="flex flex-wrap gap-2">
                                        {client.payment_methods.map((pm, idx) => (
                                            <div
                                                key={idx}
                                                className="flex items-center gap-2 px-4 py-2 bg-white/5 rounded-lg border border-white/10"
                                            >
                                                <span className="text-lg">
                                                    {COUNTRIES.find(c => c.code === pm.country)?.flag || '🌍'}
                                                </span>
                                                <div>
                                                    <p className="text-sm text-white">{pm.country}</p>
                                                    {pm.bank_name && (
                                                        <p className="text-xs text-gray-400">{pm.bank_name}</p>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>

            {/* Modal Nuevo Contacto */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="card-glass p-8 w-full max-w-md mx-4 animate-slide-up">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-2xl font-bold text-white">Nuevo Contacto</h2>
                            <button
                                onClick={() => setShowModal(false)}
                                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                            >
                                <X className="w-5 h-5 text-gray-400" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    Nombre del contacto
                                </label>
                                <input
                                    type="text"
                                    placeholder="Ej: Juan Pérez"
                                    value={newClient.name}
                                    onChange={(e) => setNewClient({ ...newClient, name: e.target.value })}
                                    className="input-glass"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    WhatsApp / Teléfono
                                </label>
                                <input
                                    type="tel"
                                    placeholder="Ej: +58 412 1234567"
                                    value={newClient.phone}
                                    onChange={(e) => setNewClient({ ...newClient, phone: e.target.value })}
                                    className="input-glass"
                                />
                            </div>
                        </div>

                        <div className="flex gap-4 mt-8">
                            <button
                                onClick={() => setShowModal(false)}
                                className="btn-secondary flex-1"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={handleAddClient}
                                className="btn-primary flex-1 flex items-center justify-center gap-2"
                                disabled={!newClient.name || !newClient.phone}
                            >
                                <Check className="w-5 h-5" />
                                Guardar
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal Agregar Destino */}
            {showPaymentModal && selectedClient && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="card-glass p-8 w-full max-w-md mx-4 animate-slide-up">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-2xl font-bold text-white">Agregar Destino</h2>
                                <p className="text-gray-400">Para: {selectedClient.name}</p>
                            </div>
                            <button
                                onClick={() => setShowPaymentModal(false)}
                                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                            >
                                <X className="w-5 h-5 text-gray-400" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    País destino
                                </label>
                                <div className="grid grid-cols-2 gap-2">
                                    {COUNTRIES.map((country) => (
                                        <button
                                            key={country.code}
                                            onClick={() => setNewPayment({ ...newPayment, country: country.code })}
                                            className={`p-3 rounded-xl flex items-center gap-3 transition-all ${newPayment.country === country.code
                                                    ? 'bg-blue-500/30 border-2 border-blue-500'
                                                    : 'bg-white/5 border border-white/10 hover:bg-white/10'
                                                }`}
                                        >
                                            <span className="text-2xl">{country.flag}</span>
                                            <span className="text-sm text-white">{country.name}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    Banco (opcional)
                                </label>
                                <input
                                    type="text"
                                    placeholder="Ej: Bancolombia, Banesco..."
                                    value={newPayment.bank_name}
                                    onChange={(e) => setNewPayment({ ...newPayment, bank_name: e.target.value })}
                                    className="input-glass"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    Número de cuenta (opcional)
                                </label>
                                <input
                                    type="text"
                                    placeholder="Ej: 0134-0001-00-1234567890"
                                    value={newPayment.account_number}
                                    onChange={(e) => setNewPayment({ ...newPayment, account_number: e.target.value })}
                                    className="input-glass"
                                />
                            </div>
                        </div>

                        <div className="flex gap-4 mt-8">
                            <button
                                onClick={() => setShowPaymentModal(false)}
                                className="btn-secondary flex-1"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={handleAddPayment}
                                className="btn-primary flex-1 flex items-center justify-center gap-2"
                                disabled={!newPayment.country}
                            >
                                <Check className="w-5 h-5" />
                                Agregar Destino
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
