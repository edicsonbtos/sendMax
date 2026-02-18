'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Card, CardContent, Stack, Button, TextField,
  Alert, CircularProgress, IconButton, Chip, Dialog, DialogTitle,
  DialogContent, DialogActions, Switch, FormControlLabel, Divider,
  Snackbar, Avatar, Tooltip,
} from '@mui/material';
import {
  Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon,
  Save as SaveIcon, Refresh as RefreshIcon, DragIndicator as DragIcon,
  AccountBalance as BankIcon, CheckCircle as ActiveIcon,
  Cancel as InactiveIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

const COUNTRIES = [
  { code: 'USA', flag: '\u{1F1FA}\u{1F1F8}', label: 'Estados Unidos', color: '#3C3B6E' },
  { code: 'VENEZUELA', flag: '\u{1F1FB}\u{1F1EA}', label: 'Venezuela', color: '#FFCD00' },
  { code: 'CHILE', flag: '\u{1F1E8}\u{1F1F1}', label: 'Chile', color: '#0039A6' },
  { code: 'PERU', flag: '\u{1F1F5}\u{1F1EA}', label: 'Per\u00FA', color: '#D91023' },
  { code: 'COLOMBIA', flag: '\u{1F1E8}\u{1F1F4}', label: 'Colombia', color: '#FCD116' },
  { code: 'MEXICO', flag: '\u{1F1F2}\u{1F1FD}', label: 'M\u00E9xico', color: '#006847' },
  { code: 'ARGENTINA', flag: '\u{1F1E6}\u{1F1F7}', label: 'Argentina', color: '#74ACDF' },
];

interface PaymentMethod {
  name: string;
  holder: string;
  details: string;
  active: boolean;
  order: number;
}

interface CountryMethods {
  methods: PaymentMethod[];
  active_count: number;
  total_count: number;
}

export default function PaymentMethodsPage() {
  const { token } = useAuth();
  const [data, setData] = useState<Record<string, CountryMethods>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });

  const [editCountry, setEditCountry] = useState<string | null>(null);
  const [editMethod, setEditMethod] = useState<PaymentMethod | null>(null);
  const [editIndex, setEditIndex] = useState<number>(-1);
  const [deleteTarget, setDeleteTarget] = useState<{ country: string; index: number } | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await apiRequest<{ ok: boolean; countries: Record<string, CountryMethods> }>('/admin/payment-methods');
      setData(res.countries || {});
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error cargando');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { if (token) fetchData(); }, [token, fetchData]);

  const saveAll = async (newData: Record<string, CountryMethods>) => {
    setSaving(true);
    try {
      const payload: Record<string, { methods: PaymentMethod[] }> = {};
      Object.entries(newData).forEach(([country, cd]) => {
        if (cd.methods.length > 0) {
          payload[country] = { methods: cd.methods };
        }
      });
      await apiRequest('/admin/payment-methods', {
        method: 'PUT',
        body: JSON.stringify({ value_json: payload }),
      });
      setSnackbar({ open: true, message: 'Guardado correctamente', severity: 'success' });
      await fetchData();
    } catch (err: unknown) {
      setSnackbar({ open: true, message: err instanceof Error ? err.message : 'Error', severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleAddMethod = (country: string) => {
    setEditCountry(country);
    setEditIndex(-1);
    setEditMethod({ name: '', holder: '', details: '', active: true, order: (data[country]?.methods?.length || 0) + 1 });
  };

  const handleEditMethod = (country: string, index: number) => {
    setEditCountry(country);
    setEditIndex(index);
    setEditMethod({ ...data[country].methods[index] });
  };

  const handleSaveMethod = async () => {
    if (!editCountry || !editMethod || !editMethod.name.trim()) return;
    const newData = { ...data };
    if (!newData[editCountry]) {
      newData[editCountry] = { methods: [], active_count: 0, total_count: 0 };
    }
    const methods = [...newData[editCountry].methods];
    if (editIndex >= 0) {
      methods[editIndex] = editMethod;
    } else {
      methods.push(editMethod);
    }
    newData[editCountry] = {
      methods,
      active_count: methods.filter(m => m.active).length,
      total_count: methods.length,
    };
    setData(newData);
    setEditCountry(null);
    setEditMethod(null);
    await saveAll(newData);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    const newData = { ...data };
    const methods = [...newData[deleteTarget.country].methods];
    methods.splice(deleteTarget.index, 1);
    methods.forEach((m, i) => { m.order = i + 1; });
    newData[deleteTarget.country] = {
      methods,
      active_count: methods.filter(m => m.active).length,
      total_count: methods.length,
    };
    setData(newData);
    setDeleteTarget(null);
    await saveAll(newData);
  };

  const handleToggleActive = async (country: string, index: number) => {
    const newData = { ...data };
    const methods = [...newData[country].methods];
    methods[index] = { ...methods[index], active: !methods[index].active };
    newData[country] = {
      methods,
      active_count: methods.filter(m => m.active).length,
      total_count: methods.length,
    };
    setData(newData);
    await saveAll(newData);
  };

  return (
    <Box className="fade-in">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Metodos de Pago</Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>
            Administra los metodos de pago por pais que ven los operadores en Telegram
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<RefreshIcon />} onClick={fetchData} disabled={loading}>
          Actualizar
        </Button>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress sx={{ color: '#4B2E83' }} />
        </Box>
      ) : (
        <Stack spacing={3}>
          {COUNTRIES.map((country) => {
            const cd = data[country.code] || { methods: [], active_count: 0, total_count: 0 };
            return (
              <Card key={country.code} sx={{ borderLeft: 4px solid  }}>
                <CardContent sx={{ p: 2.5 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
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
                      Sin metodos configurados. El bot mostrara mensaje de soporte.
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

      {/* Edit/Add Dialog */}
      <Dialog open={!!editMethod} onClose={() => { setEditMethod(null); setEditCountry(null); }} fullWidth maxWidth="sm">
        <DialogTitle sx={{ fontWeight: 700 }}>
          {editIndex >= 0 ? 'Editar Metodo' : 'Nuevo Metodo'}
          {editCountry && (
            <Chip label={COUNTRIES.find(c => c.code === editCountry)?.label} size="small" sx={{ ml: 1, fontWeight: 600 }} />
          )}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <TextField
              label="Nombre del metodo" fullWidth required
              placeholder="Ej: Zelle, Pago Movil, Transferencia"
              value={editMethod?.name || ''} onChange={(e) => setEditMethod(prev => prev ? { ...prev, name: e.target.value } : prev)}
            />
            <TextField
              label="Titular" fullWidth
              placeholder="Ej: Moises Rivero"
              value={editMethod?.holder || ''} onChange={(e) => setEditMethod(prev => prev ? { ...prev, holder: e.target.value } : prev)}
            />
            <TextField
              label="Datos de pago" fullWidth multiline rows={3}
              placeholder="Ej: Banco Mercantil\nCuenta: 0105-1234-5678\nTelefono: 04242686434"
              value={editMethod?.details || ''} onChange={(e) => setEditMethod(prev => prev ? { ...prev, details: e.target.value } : prev)}
              helperText="Usa Enter para separar lineas"
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

      {/* Delete Dialog */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Eliminar metodo</DialogTitle>
        <DialogContent>
          <Alert severity="error">Esta accion no se puede deshacer.</Alert>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setDeleteTarget(null)}>Cancelar</Button>
          <Button variant="contained" color="error" onClick={handleDeleteConfirm} disabled={saving}>
            {saving ? 'Eliminando...' : 'Eliminar'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar(s => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert onClose={() => setSnackbar(s => ({ ...s, open: false }))} severity={snackbar.severity} variant="filled">
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
