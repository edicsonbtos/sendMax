'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Stack,
  Button,
  Alert,
  CircularProgress,
  Chip,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableRow,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

interface OrderDetail {
  public_id: number | string;
  status: string;
  origin_country: string;
  dest_country: string;
  amount_origin: number;
  origin_currency: string;
  payout_dest: number;
  dest_currency: string;
  profit_usdt: number;
  created_at: string;
  updated_at?: string;
  sender_name?: string;
  receiver_name?: string;
  exchange_rate?: number;
  tx_hash_origin?: string;
  tx_hash_dest?: string;
  notes?: string;
}

interface OrderTrade {
  id: number;
  side: "BUY" | "SELL";
  fiat_currency: string;
  fiat_amount: number;
  price: number | null;
  usdt_amount: number;
  fee_usdt: number | null;
  source?: string | null;
  external_ref?: string | null;
  note?: string | null;
  created_at?: string | null;
}

interface OrderProfitRealBreakdown {
  buy_usdt: number;
  sell_usdt: number;
  fees_usdt: number;
}

interface OrderDetailApiResponse {
  order: OrderDetail;
  ledger?: any[];
  trades?: OrderTrade[];
  profit_real_usdt?: number;
  profit_real_breakdown?: OrderProfitRealBreakdown;
}
const statusColors: Record<string, 'default' | 'warning' | 'info' | 'success' | 'error'> = {
  pending_kyc: 'warning',
  pending_origin: 'warning',
  pending_dest: 'info',
  completed: 'success',
  cancelled: 'error',
  PAGADA: 'success',
  CANCELADA: 'error',
  PENDIENTE: 'warning',
  EN_PROCESO: 'info',
};

const statusLabels: Record<string, string> = {
  pending_kyc: 'KYC Pendiente',
  pending_origin: 'Pago Origen',
  pending_dest: 'Pago Destino',
  completed: 'Completada',
  cancelled: 'Cancelada',
  PAGADA: 'Pagada',
  CANCELADA: 'Cancelada',
  PENDIENTE: 'Pendiente',
  EN_PROCESO: 'En Proceso',
};

export default function OrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { apiKey } = useAuth();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [orderResp, setOrderResp] = useState<OrderDetailApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const orderId = params.id as string;

  const fetchOrder = useCallback(async () => {
    if (!orderId) return;
    setLoading(true);
    setError('');
    try {
      const data = await apiRequest<OrderDetail>(`/orders/${orderId}`);
      setOrderResp(data);
      setOrder(data.order ?? (data as any));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error desconocido';
      setError(message);
      setOrder(null);
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    if (apiKey && orderId) {
      fetchOrder();
    }
  }, [apiKey, orderId, fetchOrder]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress sx={{ color: '#4B2E83' }} />
      </Box>
    );
  }

  return (
    <Box className="fade-in">
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <Button
            variant="outlined"
            startIcon={<BackIcon />}
            onClick={() => router.push('/orders')}
          >
            Volver
          </Button>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 800 }}>
              {`Orden #${orderId}`}
            </Typography>
            <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>
              Detalle completo de la orden
            </Typography>
          </Box>
        </Stack>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={fetchOrder}
          disabled={loading}
        >
          Actualizar
        </Button>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {order && (
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Informacion de la Orden
              </Typography>
              <Chip
                label={statusLabels[order.status] || order.status}
                color={statusColors[order.status] || 'default'}
                sx={{ fontWeight: 700 }}
              />
            </Stack>

            <Divider sx={{ mb: 2 }} />

            <Table>
              <TableBody>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none', width: '30%' }}>ID Publico</TableCell>
                  <TableCell sx={{ border: 'none', fontFamily: 'monospace', fontWeight: 700 }}>{`#${order.public_id}`}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>Estado</TableCell>
                  <TableCell sx={{ border: 'none' }}>{statusLabels[order.status] || order.status}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>Pais Origen</TableCell>
                  <TableCell sx={{ border: 'none' }}>{order.origin_country}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>Pais Destino</TableCell>
                  <TableCell sx={{ border: 'none' }}>{order.dest_country}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>Monto Origen</TableCell>
                  <TableCell sx={{ border: 'none', fontWeight: 700, color: '#16A34A' }}>
                    {`${order.amount_origin?.toLocaleString('es-VE', { minimumFractionDigits: 2 })} ${order.origin_currency}`}
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>Payout Destino</TableCell>
                  <TableCell sx={{ border: 'none', fontWeight: 700, color: '#2563EB' }}>
                    {`${order.payout_dest?.toLocaleString('es-VE', { minimumFractionDigits: 2 })} ${order.dest_currency}`}
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>Ganancia USDT</TableCell>
                  <TableCell sx={{ border: 'none', fontWeight: 700, color: order.profit_usdt > 0 ? '#16A34A' : '#64748B' }}>
                    {`$${(order.profit_usdt || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
                  </TableCell>
                </TableRow>
                {order.exchange_rate && (
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>Tasa de Cambio</TableCell>
                    <TableCell sx={{ border: 'none' }}>{order.exchange_rate}</TableCell>
                  </TableRow>
                )}
                {order.sender_name && (
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>Remitente</TableCell>
                    <TableCell sx={{ border: 'none' }}>{order.sender_name}</TableCell>
                  </TableRow>
                )}
                {order.receiver_name && (
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>Beneficiario</TableCell>
                    <TableCell sx={{ border: 'none' }}>{order.receiver_name}</TableCell>
                  </TableRow>
                )}
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>Fecha de Creacion</TableCell>
                  <TableCell sx={{ border: 'none' }}>
                    {new Date(order.created_at).toLocaleString('es-VE')}
                  </TableCell>
                </TableRow>
                {order.updated_at && (
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>Ultima Actualizacion</TableCell>
                    <TableCell sx={{ border: 'none' }}>
                      {new Date(order.updated_at).toLocaleString('es-VE')}
                    </TableCell>
                  </TableRow>
                )}
                {order.tx_hash_origin && (
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>TX Hash Origen</TableCell>
                    <TableCell sx={{ border: 'none', fontFamily: 'monospace', fontSize: '0.8rem' }}>{order.tx_hash_origin}</TableCell>
                  </TableRow>
                )}
                {order.tx_hash_dest && (
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>TX Hash Destino</TableCell>
                    <TableCell sx={{ border: 'none', fontFamily: 'monospace', fontSize: '0.8rem' }}>{order.tx_hash_dest}</TableCell>
                  </TableRow>
                )}
                {order.notes && (
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none' }}>Notas</TableCell>
                    <TableCell sx={{ border: 'none' }}>{order.notes}</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {orderResp && (
        <Card sx={{ mt: 2 }}>
          <CardContent sx={{ p: 3 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Ejecución (BUY/SELL)
              </Typography>
              <Chip
                label="Registro manual / Binance"
                sx={{ fontWeight: 700, backgroundColor: "#EFEAFF", color: "#4B2E83" }}
              />
            </Stack>

            <Divider sx={{ mb: 2 }} />

            <Table size="small">
              <TableBody>
                {(orderResp.trades && orderResp.trades.length > 0) ? (
                  <>
                    {orderResp.trades.map((t) => (
                      <TableRow key={t.id}>
                        <TableCell sx={{ border: "none", width: "18%" }}>
                          <Chip
                            label={t.side}
                            size="small"
                            color={t.side === "BUY" ? "info" : "success"}
                            sx={{ fontWeight: 800 }}
                          />
                        </TableCell>
                        <TableCell sx={{ border: "none", width: "22%", fontWeight: 800 }}>
                          {t.fiat_currency}
                        </TableCell>
                        <TableCell sx={{ border: "none" }} align="right">
                          {Number(t.fiat_amount || 0).toLocaleString("es-VE", { minimumFractionDigits: 2 })}
                        </TableCell>
                        <TableCell sx={{ border: "none" }} align="right">
                          {t.price == null ? "-" : Number(t.price).toLocaleString("es-VE", { minimumFractionDigits: 2 })}
                        </TableCell>
                        <TableCell sx={{ border: "none", fontWeight: 900 }} align="right">
                          {Number(t.usdt_amount || 0).toLocaleString("es-VE", { minimumFractionDigits: 2 })}
                        </TableCell>
                        <TableCell sx={{ border: "none" }} align="right">
                          {Number(t.fee_usdt || 0).toLocaleString("es-VE", { minimumFractionDigits: 2 })}
                        </TableCell>
                      </TableRow>
                    ))}
                  </>
                ) : (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 4, color: "#64748B", border: "none" }}>
                      No hay BUY/SELL registrados para esta orden
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>

            <Divider sx={{ my: 2 }} />

            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <Card variant="outlined" sx={{ flex: 1 }}>
                <CardContent>
                  <Typography variant="body2" sx={{ color: "#64748B" }}>Profit teórico (sistema)</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 900, mt: 0.5, color: "#16A34A" }}>
                    {`$${Number(order?.profit_usdt || 0).toLocaleString("es-VE", { minimumFractionDigits: 2 })}`}
                  </Typography>
                </CardContent>
              </Card>

              <Card variant="outlined" sx={{ flex: 1 }}>
                <CardContent>
                  <Typography variant="body2" sx={{ color: "#64748B" }}>Profit real (BUY/SELL)</Typography>
                  <Typography
                    variant="h6"
                    sx={{
                      fontWeight: 900,
                      mt: 0.5,
                      color: Number(orderResp.profit_real_usdt || 0) >= 0 ? "#16A34A" : "#DC2626"
                    }}
                  >
                    {`$${Number(orderResp.profit_real_usdt || 0).toLocaleString("es-VE", { minimumFractionDigits: 2 })}`}
                  </Typography>

                  {orderResp.profit_real_breakdown && (
                    <Typography variant="caption" sx={{ color: "#64748B", display: "block", mt: 0.75 }}>
                      {`BUY: ${Number(orderResp.profit_real_breakdown.buy_usdt || 0).toFixed(2)} | SELL: ${Number(orderResp.profit_real_breakdown.sell_usdt || 0).toFixed(2)} | Fees: ${Number(orderResp.profit_real_breakdown.fees_usdt || 0).toFixed(2)}`}
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Stack>
          </CardContent>
        </Card>
      )}
      {!order && !error && (
        <Alert severity="info">
          {`No se encontro la orden con ID ${orderId}`}
        </Alert>
      )}
    </Box>
  );
}