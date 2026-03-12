'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Stack,
  IconButton,
  Button,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  CircularProgress,
  Alert,
  Tooltip,
  Snackbar,
  Switch,
  FormControlLabel,
  Avatar,
  Divider,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  DragIndicator as DragIcon,
  CheckCircle as ActiveIcon,
  Cancel as InactiveIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import api from '@/lib/api';

const COUNTRIES = [
  { code: 'VENEZUELA', label: 'Venezuela', flag: '🇻🇪', color: '#FFD700' },
  { code: 'USA', label: 'Estados Unidos', flag: '🇺🇸', color: '#3C3B6E' },
  { code: 'CHILE', label: 'Chile', flag: '🇨🇱', color: '#D52B1E' },
  { code: 'PERU', label: 'Perú', flag: '🇵🇪', color: '#D91023' },
  { code: 'COLOMBIA', label: 'Colombia', flag: '🇨🇴', color: '#FCD116' },
  { code: 'MEXICO', label: 'México', flag: '🇲🇽', color: '#006847' },
  { code: 'ARGENTINA', label: 'Argentina', flag: '🇦🇷', color: '#75AADB' },
];

interface PaymentMethod {
  name: string;
  holder: string;
  details: string;
  active: boolean;
  priority?: number;
}

interface CountryData {
  country: string;
  methods: PaymentMethod[];
  total_count: number;
  active_count: number;
}

export default function PaymentMethodsPage() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<CountryData[]>([]);

  const [editCountry, setEditCountry] = useState<string | null>(null);
  const [editIndex, setEditIndex] = useState<number>(-1);
  const [editMethod, setEditMethod] = useState<PaymentMethod | null>(null);

  const [deleteTarget, setDeleteTarget] = useState<{ country: string; index: number } | null>(null);

  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<CountryData[]>('/admin/payment-methods');
      setData(res.data || []);
    } catch (e: any) {
      console.error(e);
      setError(e.message || 'Error cargando métodos de pago');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  const handleAddMethod = (country: string) => {
    setEditCountry(country);
    setEditIndex(-1);
    setEditMethod({ name: '', holder: '', details: '', active: true });
  };

  const handleEditMethod = (country: string, index: number) => {
    const method = data.find(d => d.country === country)?.methods[index];
    if (method) {
      setEditCountry(country);
      setEditIndex(index);
      setEditMethod({ ...method });
    }
  };

  const handleSaveMethod = async () => {
    if (!editCountry || !editMethod) return;
    setSaving(true);
    try {
      const newData = [...data];
      const countryData = newData.find(d => d.country === editCountry);
      if (countryData) {
        if (editIndex >= 0) {
          countryData.methods[editIndex] = editMethod;
        } else {
          countryData.methods.push(editMethod);
        }

        await api.put(`/admin/payment-methods/${editCountry}`, { methods: countryData.methods });
        setSnackbar({ open: true, message: 'Método guardado correctamente', severity: 'success' });
        setEditMethod(null);
        setEditCountry(null);
        load();
      }
    } catch (e: any) {
      setSnackbar({ open: true, message: e.message || 'Error guardando método', severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (country: string, index: number) => {
    const countryData = data.find(d => d.country === country);
    if (!countryData) return;

    const methods = [...countryData.methods];
    methods[index].active = !methods[index].active;

    setSaving(true);
    try {
      await api.put(`/admin/payment-methods/${country}`, { methods });
      load();
    } catch (e: any) {
      setSnackbar({ open: true, message: e.message || 'Error actualizando estado', severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setSaving(true);
    try {
      const countryData = data.find(d => d.country === deleteTarget.country);
      if (countryData) {
        const methods = countryData.methods.filter((_, i) => i !== deleteTarget.index);
        await api.put(`/admin/payment-methods/${deleteTarget.country}`, { methods });
        setSnackbar({ open: true, message: 'Método eliminado', severity: 'success' });
        setDeleteTarget(null);
        load();
      }
    } catch (e: any) {
      setSnackbar({ open: true, message: e.message || 'Error eliminando método', severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box sx={{ p: 4, pb: 10 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: '#1E293B' }}>Métodos de Pago</Typography>
          <Typography variant="body2" color="text.secondary">Configuración de cuentas receptoras por país</Typography>
        </Box>
        <IconButton onClick={load} disabled={loading} color="primary" sx={{ bgcolor: '#F1F5F9' }}>
          <RefreshIcon />
        </IconButton>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 4 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}><CircularProgress /></Box>
      ) : (
        <Stack spacing={3}>
          {COUNTRIES.map((country) => {
            const cd = data.find(d => d.country === country.code) || { methods: [], total_count: 0, active_count: 0 };
            return (
              <Card key={country.code} elevation={0} sx={{ border: '1px solid #E2E8F0', borderRadius: 4 }}>
                <CardContent sx={{ p: 3 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
                    <Stack direction="row" spacing={1.5} alignItems="center">
                      <Avatar sx={{ width: 36, height: 36, fontSize: '1.2rem', bgcolor: country.color }}>
                        {country.flag}
                      </Avatar>
                      <Box>
                        <Typography variant="h6" sx={{ fontWeight: 700 }}>{country.label}</Typography>
                        <Typography variant="caption" sx={{ color: '#64748B' }}>
                          {cd.active_count} activos / {cd.total_count} total
                        </Typography>
                      </Box>
                    </Stack>
                    <Button
                      variant="outlined" startIcon={<AddIcon />} size="small"
                      onClick={() => handleAddMethod(country.code)}
                      disabled={saving}
                      sx={{ color: '#4B2E83', borderColor: '#4B2E83' }}
                    >
                      Nuevo
                    </Button>
                  </Stack>

                  {cd.methods.length === 0 ? (
                    <Alert severity="info" sx={{ fontSize: '0.85rem' }}>
                      Sin métodos configurados. El bot mostrará mensaje de soporte.
                    </Alert>
                  ) : (
                    <Stack spacing={1.5}>
                      {cd.methods.map((method, idx) => (
                        <Card key={idx} variant="outlined" sx={{
                          p: 2, opacity: method.active ? 1 : 0.6,
                          borderColor: method.active ? '#16A34A40' : '#DC262640',
                          backgroundColor: method.active ? '#F0FDF4' : '#FEF2F2',
                        }}>
                          <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                            <Stack direction="row" spacing={1.5} alignItems="flex-start" sx={{ flex: 1 }}>
                              <DragIcon sx={{ color: '#94A3B8', mt: 0.5, cursor: 'grab' }} />
                              <Box sx={{ flex: 1 }}>
                                <Stack direction="row" spacing={1} alignItems="center">
                                  <Typography sx={{ fontWeight: 700 }}>{method.name}</Typography>
                                  {method.active ? (
                                    <Chip icon={<ActiveIcon />} label="Activo" size="small" color="success" sx={{ fontWeight: 600, height: 22 }} />
                                  ) : (
                                    <Chip icon={<InactiveIcon />} label="Inactivo" size="small" color="error" sx={{ fontWeight: 600, height: 22 }} />
                                  )}
                                </Stack>
                                {method.holder && (
                                  <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>
                                    Titular: {method.holder}
                                  </Typography>
                                )}
                                {method.details && (
                                  <Typography variant="body2" sx={{ color: '#64748B', mt: 0.25, whiteSpace: 'pre-line' }}>
                                    {method.details}
                                  </Typography>
                                )}
                              </Box>
                            </Stack>
                            <Stack direction="row" spacing={0.5}>
                              <Tooltip title={method.active ? 'Desactivar' : 'Activar'}>
                                <IconButton size="small" onClick={() => handleToggleActive(country.code, idx)}>
                                  {method.active ? <ActiveIcon sx={{ color: '#16A34A' }} /> : <InactiveIcon sx={{ color: '#DC2626' }} />}
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Editar">
                                <IconButton size="small" onClick={() => handleEditMethod(country.code, idx)}>
                                  <EditIcon sx={{ color: '#4B2E83' }} />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Eliminar">
                                <IconButton size="small" onClick={() => setDeleteTarget({ country: country.code, index: idx })}>
                                  <DeleteIcon sx={{ color: '#DC2626' }} />
                                </IconButton>
                              </Tooltip>
                            </Stack>
                          </Stack>
                        </Card>
                      ))}
                    </Stack>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </Stack>
      )}

      <Dialog open={!!editMethod} onClose={() => { setEditMethod(null); setEditCountry(null); }} fullWidth maxWidth="sm">
        <DialogTitle sx={{ fontWeight: 700 }}>
          {editIndex >= 0 ? 'Editar Método' : 'Nuevo Método'}
          {editCountry && (
            <Chip label={COUNTRIES.find(c => c.code === editCountry)?.label} size="small" sx={{ ml: 1, fontWeight: 600 }} />
          )}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <TextField
              label="Nombre del método" fullWidth required
              placeholder="Ej: Zelle, Pago Móvil, Transferencia"
              value={editMethod?.name || ''} onChange={(e) => setEditMethod(prev => prev ? { ...prev, name: e.target.value } : prev)}
            />
            <TextField
              label="Titular" fullWidth
              placeholder="Ej: Moises Rivero"
              value={editMethod?.holder || ''} onChange={(e) => setEditMethod(prev => prev ? { ...prev, holder: e.target.value } : prev)}
            />
            <TextField
              label="Datos de pago" fullWidth multiline rows={3}
              placeholder="Ej: Banco Mercantil&#10;Cuenta: 0105-1234-5678&#10;Teléfono: 04242686434"
              value={editMethod?.details || ''} onChange={(e) => setEditMethod(prev => prev ? { ...prev, details: e.target.value } : prev)}
              helperText="Usa Enter para separar líneas"
            />
            <FormControlLabel
              control={<Switch checked={editMethod?.active ?? true} onChange={(e) => setEditMethod(prev => prev ? { ...prev, active: e.target.checked } : prev)} />}
              label="Activo (visible para operadores)"
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => { setEditMethod(null); setEditCountry(null); }}>Cancelar</Button>
          <Button variant="contained" onClick={handleSaveMethod} disabled={saving || !editMethod?.name?.trim()}
            startIcon={saving ? <CircularProgress size={16} /> : <SaveIcon />}
            sx={{ backgroundColor: '#4B2E83' }}>
            {saving ? 'Guardando...' : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Eliminar método</DialogTitle>
        <DialogContent>
          <Alert severity="error">Esta acción no se puede deshacer.</Alert>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setDeleteTarget(null)}>Cancelar</Button>
          <Button variant="contained" color="error" onClick={handleDeleteConfirm} disabled={saving}>
            {saving ? 'Eliminando...' : 'Eliminar'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar(s => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert onClose={() => setSnackbar(s => ({ ...s, open: false }))} severity={snackbar.severity} variant="filled">
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
