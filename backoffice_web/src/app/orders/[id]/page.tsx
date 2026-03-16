'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Box, Typography, Card, CardContent, Stack, Button, Alert,
  CircularProgress, Chip, Divider, Table, TableBody, TableCell,
  TableRow, TableHead, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField, Snackbar, IconButton, Tooltip,
  MenuItem, Select, FormControl, InputLabel, Avatar,
} from '@mui/material';
import {
  ArrowBack as BackIcon, Refresh as RefreshIcon,
  Add as AddIcon, TrendingUp as BuyIcon,
  TrendingDown as SellIcon, AccountBalanceWallet as WalletIcon,
  Receipt as TradeIcon, Info as InfoIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

/* -- Helpers ---------------------------------------------- */
const countryToCurrency: Record<string, string> = {
  VENEZUELA: 'VES', COLOMBIA: 'COP', PERU: 'PEN', CHILE: 'CLP',
  USA: 'USD', MEXICO: 'MXN', ARGENTINA: 'ARS', BRASIL: 'BRL',
  ECUADOR: 'USD', BOLIVIA: 'BOB', PANAMA: 'USD',
};

const getCurrencySymbol = (c: string) => {
  const s: Record<string, string> = {
    USD: '$', USDT: '$', COP: 'COL$', PEN: 'S/', VES: 'Bs.',
    CLP: 'CLP$', ARS: 'AR$', BRL: 'R$', MXN: 'MX$', BOB: 'Bs',
  };
  return s[c] || c;
};

const fmt = (n: number | null | undefined, currency?: string) => {
  if (n == null) return '-';
  const decimals = currency && ['COP', 'VES', 'CLP'].includes(currency) ? 0 : 2;
  return n.toLocaleString('es-VE', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
};

const fmtUsd = (n: number | null | undefined) => {
  if (n == null) return '-';
  return '$' + n.toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const getCountryInfo = (country: string) => {
  const info: Record<string, { code: string; color: string }> = {
    VENEZUELA: { code: 'VE', color: '#FFCD00' }, COLOMBIA: { code: 'CO', color: '#FCD116' },
    PERU: { code: 'PE', color: '#D91023' }, CHILE: { code: 'CL', color: '#0039A6' },
    USA: { code: 'US', color: '#3C3B6E' }, MEXICO: { code: 'MX', color: '#006847' },
    ARGENTINA: { code: 'AR', color: '#74ACDF' }, BRASIL: { code: 'BR', color: '#009B3A' },
  };
  return info[country?.toUpperCase()] || { code: (country || '??').substring(0, 2), color: '#64748B' };
};

/* -- Interfaces ------------------------------------------- */
interface OrderData {
  public_id: number;
  status: string;
  origin_country: string;
  dest_country: string;
  origin_currency: string | null;
  dest_currency: string | null;
  amount_origin: number;
  payout_dest: number;
  rate_client: number;
  commission_pct: number;
  profit_usdt: number | null;
  profit_real_usdt: number | null;
  execution_price_buy: number | null;
  execution_price_sell: number | null;
  beneficiary_text: string;
  origin_payment_proof_file_id: string;
  awaiting_paid_proof: boolean;
  awaiting_paid_proof_at: string | null;
  created_at: string;
  updated_at: string;
  paid_at: string | null;
  cancel_reason: string | null;
  origin_verified_at: string | null;
  origin_verified_by_name: string | null;
  rate_version_id: number;
  operator_user_id: number;
}

interface Trade {
  id: number;
  side: string;
  fiat_currency: string;
  fiat_amount: number;
  price: number | null;
  usdt_amount: number;
  fee_usdt: number | null;
  source: string | null;
  external_ref: string | null;
  note: string | null;
  created_at: string | null;
}

interface ProfitBreakdown {
  buy_usdt: number;
  sell_usdt: number;
  fees_usdt: number;
}

interface DetailResponse {
  order: OrderData;
  ledger: Array<Record<string, unknown>>;
  trades: Trade[];
  profit_real_usdt: number;
  profit_real_breakdown: ProfitBreakdown;
}

interface P2PPrice {
  country: string;
  fiat: string;
  buy_price: number;
  sell_price: number;
}

/* -- Status Config ---------------------------------------- */
const statusConfig: Record<string, { label: string; color: 'default' | 'warning' | 'info' | 'success' | 'error' }> = {
  CREADA: { label: 'Creada', color: 'warning' },
  ORIGEN_VERIFICANDO: { label: 'Verificando Origen', color: 'info' },
  ORIGEN_CONFIRMADO: { label: 'Origen Confirmado', color: 'info' },
  EN_PROCESO: { label: 'En Proceso', color: 'info' },
  PAGADA: { label: 'Pagada', color: 'success' },
  COMPLETADA: { label: 'Completada', color: 'success' },
  CANCELADA: { label: 'Cancelada', color: 'error' },
};

/* -- Component -------------------------------------------- */
export default function OrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { apiKey } = useAuth();

  const [data, setData] = useState<DetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Trade modal
  const [tradeOpen, setTradeOpen] = useState(false);
  const [tradeSide, setTradeSide] = useState<'BUY' | 'SELL'>('BUY');
  const [tradeFiat, setTradeFiat] = useState('');
  const [tradeFiatAmount, setTradeFiatAmount] = useState('');
  const [tradePrice, setTradePrice] = useState('');
  const [tradeUsdtAmount, setTradeUsdtAmount] = useState('');
  const [tradeFee, setTradeFee] = useState('0');
  const [tradeSource, setTradeSource] = useState('binance_p2p');
  const [tradeNote, setTradeNote] = useState('');
  const [tradeRef, setTradeRef] = useState('');
  const [tradeProcessing, setTradeProcessing] = useState(false);

  // P2P prices
  const [p2pPrices, setP2pPrices] = useState<P2PPrice[]>([]);

  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });

  const orderId = params.id as string;

  /* -- Fetch ---------------------------------------------- */
  const fetchOrder = useCallback(async () => {
    if (!orderId) return;
    setLoading(true);
    setError('');
    try {
      const resp = await apiRequest<DetailResponse>('/orders/' + orderId);
      setData(resp);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    if (apiKey && orderId) fetchOrder();
  }, [apiKey, orderId, fetchOrder]);

  /* -- Derived -------------------------------------------- */
  const order = data?.order || null;
  const trades = data?.trades || [];
  const profitReal = data?.profit_real_usdt ?? null;
  const breakdown = data?.profit_real_breakdown || null;

  const originCurrency = useMemo(() => {
    if (order?.origin_currency) return order.origin_currency;
    return countryToCurrency[order?.origin_country || ''] || '???';
  }, [order]);

  const destCurrency = useMemo(() => {
    if (order?.dest_currency) return order.dest_currency;
    return countryToCurrency[order?.dest_country || ''] || '???';
  }, [order]);

  /* -- Trade Modal ---------------------------------------- */
  const openTradeModal = (side: 'BUY' | 'SELL') => {
    setTradeSide(side);
    const currency = side === 'BUY' ? originCurrency : destCurrency;
    setTradeFiat(currency);

    if (side === 'BUY' && order) {
      setTradeFiatAmount(String(order.amount_origin));
    } else if (side === 'SELL' && order) {
      setTradeFiatAmount(String(order.payout_dest));
    }

    // Buscar precio P2P
    const country = side === 'BUY' ? order?.origin_country : order?.dest_country;
    const p2p = p2pPrices.find((p) => p.country === country);
    if (p2p) {
      const price = side === 'BUY' ? p2p.buy_price : p2p.sell_price;
      setTradePrice(String(price));
      const fiatAmt = side === 'BUY' ? order?.amount_origin || 0 : order?.payout_dest || 0;
      const usdtAmt = fiatAmt / price;
      setTradeUsdtAmount(usdtAmt.toFixed(2));
    } else {
      setTradePrice('');
      setTradeUsdtAmount('');
    }

    setTradeFee('0');
    setTradeSource('binance_p2p');
    setTradeNote('');
    setTradeRef('');
    setTradeOpen(true);
  };

  // Auto-calculate USDT when price or amount changes
  const recalcUsdt = (fiatAmt: string, price: string) => {
    const f = parseFloat(fiatAmt);
    const p = parseFloat(price);
    if (f > 0 && p > 0) {
      setTradeUsdtAmount((f / p).toFixed(2));
    }
  };

  const handleSubmitTrade = async () => {
    if (!order) return;
    setTradeProcessing(true);
    try {
      await apiRequest('/orders/' + order.public_id + '/trades', {
        method: 'POST',
        body: JSON.stringify({
          side: tradeSide,
          fiat_currency: tradeFiat,
          fiat_amount: parseFloat(tradeFiatAmount),
          price: parseFloat(tradePrice) || null,
          usdt_amount: parseFloat(tradeUsdtAmount),
          fee_usdt: parseFloat(tradeFee) || 0,
          source: tradeSource || null,
          external_ref: tradeRef || null,
          note: tradeNote || null,
        }),
      });
      setSnackbar({ open: true, message: 'Trade ' + tradeSide + ' registrado correctamente', severity: 'success' });
      setTradeOpen(false);
      fetchOrder();
    } catch (err: unknown) {
      setSnackbar({ open: true, message: err instanceof Error ? err.message : 'Error', severity: 'error' });
    } finally {
      setTradeProcessing(false);
    }
  };

  /* -- Fetch P2P Prices ----------------------------------- */
  useEffect(() => {
    if (!order) return;
    const fetchPrices = async () => {
      try {
        const countries = [order.origin_country, order.dest_country];
        const prices: P2PPrice[] = [];
        for (const country of countries) {
          try {
            const resp = await apiRequest<{ items?: P2PPrice[] }>('/metrics/p2p-prices?country=' + country);
            if (resp?.items) prices.push(...resp.items);
          } catch {
            // ignore
          }
        }
        setP2pPrices(prices);
      } catch {
        // ignore
      }
    };
    fetchPrices();
  }, [order]);

  /* -- Render --------------------------------------------- */
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress sx={{ color: '#4B2E83' }} />
      </Box>
    );
  }

  const st = statusConfig[order?.status || ''] || { label: order?.status || '?', color: 'default' as const };

  return (
    <Box className="fade-in">
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <Button variant="outlined" startIcon={<BackIcon />} onClick={() => router.push('/orders')}>Volver</Button>
          <Box>
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="h4" sx={{ fontWeight: 800, fontFamily: 'monospace' }}>{'#' + orderId}</Typography>
              <Chip label={st.label} color={st.color} sx={{ fontWeight: 700 }} />
            </Stack>
            <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>
              {order ? new Date(order.created_at).toLocaleString('es-VE') : ''}
            </Typography>
          </Box>
        </Stack>
        <Button variant="contained" startIcon={<RefreshIcon />} onClick={fetchOrder} disabled={loading}>Actualizar</Button>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {order && (
        <>
          {/* Ruta y Montos */}
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} alignItems="center" justifyContent="center">
                {/* Origen */}
                <Card variant="outlined" sx={{ flex: 1, width: '100%', borderColor: '#16A34A40', backgroundColor: '#F0FDF4' }}>
                  <CardContent sx={{ p: 2.5, textAlign: 'center' }}>
                    <Stack direction="row" spacing={1} alignItems="center" justifyContent="center" sx={{ mb: 1 }}>
                      <Avatar sx={{ width: 28, height: 28, fontSize: '0.7rem', fontWeight: 800, bgcolor: getCountryInfo(order.origin_country).color }}>
                        {getCountryInfo(order.origin_country).code}
                      </Avatar>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>{order.origin_country}</Typography>
                    </Stack>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>Monto Origen</Typography>
                    <Typography variant="h4" sx={{ fontWeight: 800, color: '#16A34A' }}>
                      {getCurrencySymbol(originCurrency) + ' ' + fmt(order.amount_origin, originCurrency)}
                    </Typography>
                    <Chip label={originCurrency} size="small" sx={{ mt: 1, fontWeight: 700, backgroundColor: '#16A34A15', color: '#16A34A' }} />
                  </CardContent>
                </Card>

                {/* Flecha */}
                <Typography variant="h4" sx={{ color: '#94A3B8' }}>{'-->'}</Typography>

                {/* Destino */}
                <Card variant="outlined" sx={{ flex: 1, width: '100%', borderColor: '#2563EB40', backgroundColor: '#EFF6FF' }}>
                  <CardContent sx={{ p: 2.5, textAlign: 'center' }}>
                    <Stack direction="row" spacing={1} alignItems="center" justifyContent="center" sx={{ mb: 1 }}>
                      <Avatar sx={{ width: 28, height: 28, fontSize: '0.7rem', fontWeight: 800, bgcolor: getCountryInfo(order.dest_country).color }}>
                        {getCountryInfo(order.dest_country).code}
                      </Avatar>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>{order.dest_country}</Typography>
                    </Stack>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>Payout Destino</Typography>
                    <Typography variant="h4" sx={{ fontWeight: 800, color: '#2563EB' }}>
                      {getCurrencySymbol(destCurrency) + ' ' + fmt(order.payout_dest, destCurrency)}
                    </Typography>
                    <Chip label={destCurrency} size="small" sx={{ mt: 1, fontWeight: 700, backgroundColor: '#2563EB15', color: '#2563EB' }} />
                  </CardContent>
                </Card>
              </Stack>
            </CardContent>
          </Card>

          {/* Detalles */}
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} sx={{ mb: 3 }}>
            {/* Info General */}
            <Card sx={{ flex: 1 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Informacion General</Typography>
                <Divider sx={{ mb: 2 }} />
                <Table size="small">
                  <TableBody>
                    {[
                      ['Beneficiario', order.beneficiary_text || '-'],
                      ['Tasa Cliente', order.rate_client ? String(order.rate_client) : '-'],
                      ['Comision', order.commission_pct ? (Number(order.commission_pct) * 100).toFixed(1) + '%' : '-'],
                      ['Version Tasa', '#' + order.rate_version_id],
                      ['Operador ID', String(order.operator_user_id)],
                      ['Creada', new Date(order.created_at).toLocaleString('es-VE')],
                      ['Actualizada', new Date(order.updated_at).toLocaleString('es-VE')],
                      ['Pagada', order.paid_at ? new Date(order.paid_at).toLocaleString('es-VE') : 'No'],
                      ['Origen Verificado', order.origin_verified_at ? new Date(order.origin_verified_at).toLocaleString('es-VE') + ' por ' + (order.origin_verified_by_name || '?') : 'No'],
                    ].map(([label, value], i) => (
                      <TableRow key={i}>
                        <TableCell sx={{ fontWeight: 600, color: '#64748B', border: 'none', width: '40%', py: 0.75 }}>{label}</TableCell>
                        <TableCell sx={{ border: 'none', py: 0.75, fontWeight: 500 }}>{value}</TableCell>
                      </TableRow>
                    ))}
                    {order.cancel_reason && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600, color: '#DC2626', border: 'none', py: 0.75 }}>Razon Cancelacion</TableCell>
                        <TableCell sx={{ border: 'none', py: 0.75, color: '#DC2626' }}>{order.cancel_reason}</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {/* Ganancia Real */}
            <Card sx={{ flex: 1 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Ganancia Real</Typography>
                <Divider sx={{ mb: 2 }} />

                <Box sx={{ textAlign: 'center', py: 2 }}>
                  <Typography variant="caption" sx={{ color: '#64748B', textTransform: 'uppercase', letterSpacing: 1 }}>Profit Real (BUY - SELL - Fees)</Typography>
                  <Typography variant="h3" sx={{
                    fontWeight: 900, mt: 1,
                    color: profitReal == null ? '#94A3B8' : profitReal >= 0 ? '#16A34A' : '#DC2626',
                  }}>
                    {profitReal == null ? 'Sin trades' : fmtUsd(profitReal)}
                  </Typography>
                </Box>

                {breakdown && (
                  <>
                    <Divider sx={{ my: 2 }} />
                    <Stack spacing={1}>
                      <Stack direction="row" justifyContent="space-between">
                        <Typography variant="body2" sx={{ color: '#16A34A', fontWeight: 600 }}>BUY (compra USDT)</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>{fmtUsd(breakdown.buy_usdt)}</Typography>
                      </Stack>
                      <Stack direction="row" justifyContent="space-between">
                        <Typography variant="body2" sx={{ color: '#DC2626', fontWeight: 600 }}>SELL (venta USDT)</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>{fmtUsd(breakdown.sell_usdt)}</Typography>
                      </Stack>
                      <Stack direction="row" justifyContent="space-between">
                        <Typography variant="body2" sx={{ color: '#F59E0B', fontWeight: 600 }}>Fees</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>{fmtUsd(breakdown.fees_usdt)}</Typography>
                      </Stack>
                    </Stack>
                  </>
                )}

                {order.execution_price_buy || order.execution_price_sell ? (
                  <>
                    <Divider sx={{ my: 2 }} />
                    <Stack spacing={1}>
                      {order.execution_price_buy && (
                        <Stack direction="row" justifyContent="space-between">
                          <Typography variant="caption" sx={{ color: '#64748B' }}>Precio Compra</Typography>
                          <Typography variant="caption" sx={{ fontWeight: 700 }}>{fmt(Number(order.execution_price_buy))}</Typography>
                        </Stack>
                      )}
                      {order.execution_price_sell && (
                        <Stack direction="row" justifyContent="space-between">
                          <Typography variant="caption" sx={{ color: '#64748B' }}>Precio Venta</Typography>
                          <Typography variant="caption" sx={{ fontWeight: 700 }}>{fmt(Number(order.execution_price_sell))}</Typography>
                        </Stack>
                      )}
                    </Stack>
                  </>
                ) : null}
              </CardContent>
            </Card>
          </Stack>

          {/* Trades */}
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <TradeIcon sx={{ color: '#4B2E83' }} />
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>Trades (BUY / SELL)</Typography>
                  <Chip label={trades.length + ' trades'} size="small" variant="outlined" sx={{ fontWeight: 700 }} />
                </Stack>
                <Stack direction="row" spacing={1}>
                  <Button size="small" variant="outlined" startIcon={<BuyIcon />}
                    onClick={() => openTradeModal('BUY')}
                    sx={{ color: '#16A34A', borderColor: '#16A34A' }}>
                    Registrar BUY
                  </Button>
                  <Button size="small" variant="outlined" startIcon={<SellIcon />}
                    onClick={() => openTradeModal('SELL')}
                    sx={{ color: '#DC2626', borderColor: '#DC2626' }}>
                    Registrar SELL
                  </Button>
                </Stack>
              </Stack>

              <Divider sx={{ mb: 2 }} />

              {trades.length === 0 ? (
                <Alert severity="warning" sx={{ fontSize: '0.85rem' }}>
                  No hay trades registrados. Registra BUY (compra de USDT con fiat origen) y SELL (venta de USDT por fiat destino) para calcular la ganancia real.
                </Alert>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700 }}>Tipo</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Moneda</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>Monto Fiat</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>Precio</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>USDT</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>Fee</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Fuente</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Fecha</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {trades.map((t) => (
                      <TableRow key={t.id} hover>
                        <TableCell>
                          <Chip label={t.side} size="small"
                            sx={{
                              fontWeight: 800,
                              backgroundColor: t.side === 'BUY' ? '#16A34A15' : '#DC262615',
                              color: t.side === 'BUY' ? '#16A34A' : '#DC2626',
                            }} />
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>{t.fiat_currency}</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600 }}>
                          {getCurrencySymbol(t.fiat_currency) + ' ' + fmt(t.fiat_amount, t.fiat_currency)}
                        </TableCell>
                        <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                          {t.price ? fmt(t.price) : '-'}
                        </TableCell>
                        <TableCell align="right" sx={{ fontWeight: 800, color: '#4B2E83' }}>
                          {fmtUsd(t.usdt_amount)}
                        </TableCell>
                        <TableCell align="right" sx={{ color: '#F59E0B' }}>
                          {t.fee_usdt ? fmtUsd(t.fee_usdt) : '-'}
                        </TableCell>
                        <TableCell>
                          <Chip label={t.source || 'manual'} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                        </TableCell>
                        <TableCell sx={{ color: '#64748B', fontSize: '0.8rem' }}>
                          {t.created_at ? new Date(t.created_at).toLocaleString('es-VE', { hour: '2-digit', minute: '2-digit' }) : '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {!order && !error && <Alert severity="info">{'No se encontro la orden #' + orderId}</Alert>}

      {/* Trade Modal */}
      <Dialog open={tradeOpen} onClose={() => setTradeOpen(false)} fullWidth maxWidth="sm" PaperProps={{ sx: { borderRadius: 3 } }}>
        <DialogTitle sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box sx={{
            backgroundColor: tradeSide === 'BUY' ? '#16A34A15' : '#DC262615',
            borderRadius: '10px', p: 0.75, display: 'flex',
          }}>
            {tradeSide === 'BUY'
              ? <BuyIcon sx={{ color: '#16A34A', fontSize: 22 }} />
              : <SellIcon sx={{ color: '#DC2626', fontSize: 22 }} />
            }
          </Box>
          {'Registrar ' + tradeSide + ' - Orden #' + orderId}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <Alert severity="info" icon={<InfoIcon />} sx={{ fontSize: '0.85rem' }}>
              {tradeSide === 'BUY'
                ? 'BUY = Comprar USDT con fiat de origen (' + originCurrency + '). El cliente te pago en fiat, tu compras USDT.'
                : 'SELL = Vender USDT por fiat de destino (' + destCurrency + '). Tu vendes USDT para pagar al beneficiario.'
              }
            </Alert>

            <Stack direction="row" spacing={2}>
              <TextField label="Moneda Fiat" value={tradeFiat} onChange={(e) => setTradeFiat(e.target.value)}
                size="small" sx={{ width: 120 }} />
              <TextField label="Monto Fiat" type="number" value={tradeFiatAmount} fullWidth
                onChange={(e) => { setTradeFiatAmount(e.target.value); recalcUsdt(e.target.value, tradePrice); }}
                slotProps={{ input: { sx: { fontSize: '1.1rem', fontWeight: 700 } } }} />
            </Stack>

            <Stack direction="row" spacing={2}>
              <TextField label="Precio (fiat/USDT)" type="number" value={tradePrice} fullWidth
                onChange={(e) => { setTradePrice(e.target.value); recalcUsdt(tradeFiatAmount, e.target.value); }}
                helperText={p2pPrices.length > 0 ? 'Precio P2P cargado automaticamente' : 'Ingresa el precio manualmente'} />
              <TextField label="USDT Total" type="number" value={tradeUsdtAmount} fullWidth
                onChange={(e) => setTradeUsdtAmount(e.target.value)}
                slotProps={{ input: { sx: { fontSize: '1.1rem', fontWeight: 700, color: '#4B2E83' } } }} />
            </Stack>

            <Stack direction="row" spacing={2}>
              <TextField label="Fee USDT" type="number" value={tradeFee} sx={{ width: 150 }}
                onChange={(e) => setTradeFee(e.target.value)} size="small" />
              <FormControl size="small" fullWidth>
                <InputLabel>Fuente</InputLabel>
                <Select value={tradeSource} onChange={(e) => setTradeSource(e.target.value)} label="Fuente">
                  <MenuItem value="binance_p2p">Binance P2P</MenuItem>
                  <MenuItem value="binance_spot">Binance Spot</MenuItem>
                  <MenuItem value="manual">Manual</MenuItem>
                  <MenuItem value="otro">Otro</MenuItem>
                </Select>
              </FormControl>
            </Stack>

            <TextField label="Referencia Externa (opcional)" value={tradeRef} fullWidth size="small"
              onChange={(e) => setTradeRef(e.target.value)} placeholder="Ej: ID de orden Binance, hash..." />

            <TextField label="Nota (opcional)" value={tradeNote} fullWidth size="small" multiline rows={2}
              onChange={(e) => setTradeNote(e.target.value)} />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2.5, gap: 1 }}>
          <Button onClick={() => setTradeOpen(false)} color="inherit" disabled={tradeProcessing}>Cancelar</Button>
          <Button onClick={handleSubmitTrade} variant="contained" disabled={tradeProcessing || !tradeFiatAmount || !tradeUsdtAmount}
            sx={{
              backgroundColor: tradeSide === 'BUY' ? '#16A34A' : '#DC2626', fontWeight: 700,
              '&:hover': { backgroundColor: tradeSide === 'BUY' ? '#16A34ACC' : '#DC2626CC' },
            }}>
            {tradeProcessing ? 'Registrando...' : 'Registrar ' + tradeSide}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar((s) => ({ ...s, open: false }))} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert onClose={() => setSnackbar((s) => ({ ...s, open: false }))} severity={snackbar.severity} variant="filled" sx={{ width: '100%', fontWeight: 600 }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
