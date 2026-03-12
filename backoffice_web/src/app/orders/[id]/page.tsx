'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Stack,
  Grid,
  CircularProgress,
  Alert,
  IconButton,
  Button,
  Chip,
  Divider,
  Paper,
  Avatar,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  CheckCircle as PaidIcon,
  Cancel as CancelIcon,
  Receipt as ReceiptIcon,
  Person as PersonIcon,
  Public as WorldIcon,
  AttachMoney as AmountIcon,
  Notes as NotesIcon,
  AccountBalance as BankIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import api from '@/lib/api';

interface OrderDetail {
  id: number;
  public_id: number;
  operator_user_id: number;
  operator_alias: string;
  origin_country: string;
  dest_country: string;
  amount_origin: number;
  rate_client: number;
  payout_dest: number;
  beneficiary_text: string;
  status: string;
  created_at: string;
  origin_payment_proof_file_id: string | null;
  dest_payment_proof_file_id: string | null;
  paid_at: string | null;
  cancel_reason: string | null;
  profit_usdt: number | null;
}

export default function OrderDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { token } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [order, setOrder] = useState<OrderDetail | null>(null);
  
  const [profitOpen, setProfitOpen] = useState(false);
  const [profitVal, setProfitVal] = useState("");
  const [saving, setSaving] = useState(false);
  
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<OrderDetail>(`/orders/${id}`);
      setOrder(res.data);
      if (res.data.profit_usdt) setProfitVal(res.data.profit_usdt.toString());
    } catch (e: any) {
      setError(e.message || 'Error cargando orden');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (token && id) load();
  }, [token, id, load]);

  const handleUpdateProfit = async () => {
    setSaving(true);
    try {
      await api.put(`/orders/${id}/profit`, { profit_usdt: parseFloat(profitVal) });
      setProfitOpen(false);
      load();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}><CircularProgress /></Box>;
  if (!order) return <Box sx={{ p: 4 }}><Alert severity="error">Escalabilidad de orden no encontrada</Alert></Box>;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PAGADA': return 'success';
      case 'CANCELADA': return 'error';
      case 'CREADA': return 'info';
      default: return 'warning';
    }
  };

  return (
    <Box sx={{ p: 4 }}>
      <Stack direction="row" spacing={2} sx={{ mb: 4 }} alignItems="center">
        <IconButton onClick={() => router.back()} sx={{ bgcolor: '#F1F5F9' }}>
          <BackIcon />
        </IconButton>
        <Typography variant="h4" sx={{ fontWeight: 800 }}>Orden #{order.public_id}</Typography>
        <Chip label={order.status} color={getStatusColor(order.status) as any} sx={{ fontWeight: 800 }} />
      </Stack>

      <Grid container spacing={4}>
        {/* Left: General Info */}
        <Grid size={{ xs: 12, md: 7 }}>
          <Stack spacing={4}>
            <Card elevation={0} sx={{ border: '1px solid #E2E8F0', borderRadius: 4 }}>
              <CardContent sx={{ p: 4 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }} icon={<ReceiptIcon />}>Detalles de la Operación</Typography>
                
                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Ruta</Typography>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <WorldIcon sx={{ fontSize: 18, color: '#64748B' }} />
                      <Typography sx={{ fontWeight: 700 }}>{order.origin_country} → {order.dest_country}</Typography>
                    </Stack>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Fecha</Typography>
                    <Typography sx={{ fontWeight: 600 }}>{new Date(order.created_at).toLocaleString()}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Monto Origen</Typography>
                    <Typography variant="h5" sx={{ fontWeight: 800, color: '#0052FF' }}>
                      ${order.amount_origin.toLocaleString()} {order.origin_country === 'VENEZUELA' ? 'Bs' : 'USD'}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Tasa Aplicada</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>{order.rate_client.toLocaleString()}</Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Divider sx={{ my: 1 }} />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Total a Pagar</Typography>
                    <Typography variant="h5" sx={{ fontWeight: 800, color: '#10B981' }}>
                      {order.payout_dest.toLocaleString()} {order.dest_country === 'VENEZUELA' ? 'Bs' : 'USD'}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Operator</Typography>
                    <Typography sx={{ fontWeight: 700 }}>@{order.operator_alias}</Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>

            <Card elevation={0} sx={{ border: '1px solid #E2E8F0', borderRadius: 4 }}>
              <CardContent sx={{ p: 4 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Beneficiario / Datos de Destino</Typography>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#F8FAFC', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                  {order.beneficiary_text}
                </Paper>
              </CardContent>
            </Card>
          </Stack>
        </Grid>

        {/* Right: Actions & Profits */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Stack spacing={4}>
            <Card elevation={0} sx={{ border: '1px solid #E2E8F0', borderRadius: 4, bgcolor: '#EEF2FF' }}>
              <CardContent sx={{ p: 4 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>Ganancia (Profit)</Typography>
                  <Button variant="outlined" size="small" onClick={() => setProfitOpen(true)}>Editar</Button>
                </Stack>
                <Typography variant="h3" sx={{ fontWeight: 900, color: '#4338CA' }}>
                  ${order.profit_usdt ? order.profit_usdt.toFixed(2) : '0.00'}
                </Typography>
                <Typography variant="caption" color="text.secondary">Ganancia neta estimada en USDT para esta operación</Typography>
              </CardContent>
            </Card>

            {order.status === 'CANCELADA' && (
              <Alert severity="error" variant="outlined" sx={{ borderRadius: 4 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Motivo de cancelación:</Typography>
                {order.cancel_reason}
              </Alert>
            )}

            <Card elevation={0} sx={{ border: '1px solid #E2E8F0', borderRadius: 4 }}>
              <CardContent sx={{ p: 4 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>Comprobantes</Typography>
                <Stack spacing={2}>
                  <Button 
                    fullWidth variant="outlined" disabled={!order.origin_payment_proof_file_id}
                    onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/admin/media/${order.origin_payment_proof_file_id}`, '_blank')}
                  >
                    Ver Comprobante Origen
                  </Button>
                  <Button 
                    fullWidth variant="outlined" disabled={!order.dest_payment_proof_file_id}
                    onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/admin/media/${order.dest_payment_proof_file_id}`, '_blank')}
                  >
                    Ver Comprobante Destino
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          </Stack>
        </Grid>
      </Grid>

      <Dialog open={profitOpen} onClose={() => setProfitOpen(false)}>
        <DialogTitle>Ajustar Profit USDT</DialogTitle>
        <DialogContent>
          <TextField 
            autoFocus margin="dense" label="Profit en USDT" type="number" 
            fullWidth variant="outlined" value={profitVal} 
            onChange={(e) => setProfitVal(e.target.value)} 
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setProfitOpen(false)}>Cancelar</Button>
          <Button onClick={handleUpdateProfit} variant="contained" disabled={saving}>Guardar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}