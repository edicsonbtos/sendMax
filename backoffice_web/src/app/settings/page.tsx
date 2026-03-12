'use client';

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Stack,
  TextField,
  Button,
  CircularProgress,
  Alert,
  Divider,
  Paper,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
} from "@mui/material";
import {
  Refresh as RefreshIcon,
  Save as SaveIcon,
  Sync as SyncIcon,
  SettingsSuggest as EngineIcon,
  Percent as MarginIcon,
  History as HistoryIcon,
  Check as CheckIcon,
  CurrencyExchange as CashIcon,
} from "@mui/icons-material";
import { useAuth } from "@/components/AuthProvider";
import api, { apiRequest } from "@/lib/api";

interface RateVersion {
  id: number;
  kind: string;
  reason: string;
  is_active: boolean;
  created_at: string;
}

function CashDeliveryPanel({ saving, setSaving, setError, setSuccess }: any) {
  const [cashDeliveryEnable, setCashDeliveryEnable] = useState(false);
  const [loading, setLoading] = useState(true);

  React.useEffect(() => {
    async function init() {
      try {
        const val = await api.get('/admin/settings/cash_delivery');
        setCashDeliveryEnable(val.data === 'true' || val.data === true);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    }
    init();
  }, []);

  const handleToggle = async (val: boolean) => {
    setSaving(true);
    setCashDeliveryEnable(val);
    try {
      await api.put('/admin/settings/cash_delivery', { value: val ? 'true' : 'false' });
      setSuccess("Configuración de entrega en efectivo actualizada");
    } catch (e: any) {
      setError(e.message || "Error guardando cache delivery config");
    } finally { setSaving(false); }
  };

  if (loading) return null;

  return (
    <Card variant="outlined" sx={{ p: 2, bgcolor: "#F8FAFC" }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Stack direction="row" spacing={1.5} alignItems="center">
          <CashIcon sx={{ color: "#0052FF" }} />
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Entrega en Efectivo (USD)</Typography>
            <Typography variant="caption" color="text.secondary">Habilitar/Deshabilitar esta opción para operadores</Typography>
          </Box>
        </Stack>
        <Switch checked={cashDeliveryEnable} onChange={(e) => handleToggle(e.target.checked)} disabled={saving} />
      </Stack>
    </Card>
  );
}

export default function SettingsPage() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [activeVersion, setActiveVersion] = useState<RateVersion | null>(null);
  const [history, setHistory] = useState<RateVersion[]>([]);

  // Form states
  const [marginDefault, setMarginDefault] = useState("10.0");
  const [marginDestVenez, setMarginDestVenez] = useState("6.0");
  const [marginRouteUsaVenez, setMarginRouteUsaVenez] = useState("10.0");
  const [regenerateNow, setRegenerateNow] = useState(true);

  // Splits
  const [opWithSponsor, setOpWithSponsor] = useState("35");
  const [sponsorPct, setSponsorPct] = useState("15");
  const [opSolo, setOpSolo] = useState("50");

  const [confirmOpen, setConfirmOpen] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiRequest<{
        active: RateVersion;
        recent: RateVersion[];
        margins: any;
        profit_split: any;
      }>('/admin/settings/advanced');

      setActiveVersion(data.active);
      setHistory(data.recent);
      setMarginDefault(data.margins.margin_default || "10.0");
      setMarginDestVenez(data.margins.margin_dest_venez || "6.0");
      setMarginRouteUsaVenez(data.margins.margin_route_usa_venez || "10.0");

      setOpWithSponsor(data.profit_split.operator_with_sponsor || "35");
      setSponsorPct(data.profit_split.sponsor_percentage || "15");
      setOpSolo(data.profit_split.operator_solo || "50");

    } catch (e: any) {
      setError(e.message || "Error cargando configuración");
    } finally {
      setLoading(false);
    }
  };

  const manualRegen = async () => {
    setSaving(true);
    try {
      await api.post('/admin/rates/regenerate', { reason: "Manual regen from Admin Panel" });
      setSuccess("Proceso de regeneración iniciado correctamente");
      load();
    } catch (e: any) {
      setError(e.message || "Error regenerando tasas");
    } finally { setSaving(false); }
  };

  const saveMargins = async () => {
    setSaving(true);
    setConfirmOpen(false);
    try {
      await api.put('/admin/settings/margins', {
        margin_default: marginDefault,
        margin_dest_venez: marginDestVenez,
        margin_route_usa_venez: marginRouteUsaVenez,
        regenerate: regenerateNow
      });
      setSuccess("Márgenes actualizados correctamente");
      load();
    } catch (e: any) {
      setError(e.message || "Error guardando márgenes");
    } finally { setSaving(false); }
  };

  const saveProfitSplit = async () => {
    setSaving(true);
    try {
      const w_sp = parseFloat(opWithSponsor);
      const sp = parseFloat(sponsorPct);
      const ops = parseFloat(opSolo);

      if (w_sp + sp !== 100 && w_sp + sp !== ops) {
         // logic error but allow it if they want
      }

      await api.put('/admin/settings/profit-split', {
        operator_with_sponsor: w_sp,
        sponsor_percentage: sp,
        operator_solo: ops,
      });
      setSuccess("Distribución de profit actualizada");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error guardando profit split");
    } finally {
      setSaving(false);
    }
  }

  const formatDate = (ds: string) => new Date(ds).toLocaleString();

  React.useEffect(() => { if (token) load(); }, [token]);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 10 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box className="fade-in" sx={{ p: 4, pb: 6 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>Configuración Avanzada</Typography>
          <Typography variant="body2" color="text.secondary">Gestión de márgenes, tasas y distribución de ganancias</Typography>
        </Box>
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={load} disabled={saving}>
          Actualizar datos
        </Button>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 3 }}>{success}</Alert>}

      <Stack spacing={4}>
        {/* Tasas Activas */}
        <Paper sx={{ p: 3, borderLeft: "4px solid #4B2E83" }}>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
            <EngineIcon color="primary" />
            <Typography variant="h6" sx={{ fontWeight: 700 }}>Estado de Tasas</Typography>
          </Stack>

          <Stack direction="row" spacing={4} sx={{ mb: 3 }}>
            <Box>
              <Typography variant="caption" color="text.secondary">Versión Activa</Typography>
              <Typography variant="h5" sx={{ fontWeight: 800 }}>
                {activeVersion ? `#${activeVersion.id}` : "Ninguna"}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Generada el</Typography>
              <Typography variant="body1" sx={{ fontWeight: 600 }}>
                {activeVersion ? formatDate(activeVersion.created_at) : "-"}
              </Typography>
            </Box>
            <Box sx={{ flex: 1, textAlign: "right" }}>
              <Button
                variant="contained"
                color="secondary"
                startIcon={<SyncIcon />}
                onClick={manualRegen}
                disabled={saving}
              >
                Regenerar Tasas Ahora
              </Button>
            </Box>
          </Stack>

          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 700 }}>Historial Reciente</Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Tipo</TableCell>
                  <TableCell>Razón</TableCell>
                  <TableCell>Fecha</TableCell>
                  <TableCell>Estado</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {history.map((v) => (
                  <TableRow key={v.id}>
                    <TableCell>#{v.id}</TableCell>
                    <TableCell><Chip label={v.kind} size="small" variant="outlined" /></TableCell>
                    <TableCell sx={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {v.reason || "-"}
                    </TableCell>
                    <TableCell>{formatDate(v.created_at)}</TableCell>
                    <TableCell>
                      {v.is_active ? <Chip label="Activa" size="small" color="success" /> : <Typography variant="caption" color="text.secondary">Inactiva</Typography>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>

        {/* Márgenes Generales */}
        <Paper sx={{ p: 3, borderLeft: "4px solid #16A34A" }}>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
            <MarginIcon sx={{ color: "#16A34A" }} />
            <Typography variant="h6" sx={{ fontWeight: 700 }}>Márgenes Globales</Typography>
          </Stack>

          <Stack direction="row" spacing={3} sx={{ mb: 3 }}>
            <TextField
              label="Margen General (%)"
              value={marginDefault}
              onChange={(e) => setMarginDefault(e.target.value)}
              InputProps={{ endAdornment: "%" }}
              size="small"
              fullWidth
            />
            <TextField
              label="Destino VENEZUELA (%)"
              value={marginDestVenez}
              onChange={(e) => setMarginDestVenez(e.target.value)}
              InputProps={{ endAdornment: "%" }}
              size="small"
              fullWidth
            />
            <TextField
              label="Ruta USA -> VE (%)"
              value={marginRouteUsaVenez}
              onChange={(e) => setMarginRouteUsaVenez(e.target.value)}
              InputProps={{ endAdornment: "%" }}
              size="small"
              fullWidth
            />
          </Stack>

          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <FormControlLabel
              control={<Checkbox checked={regenerateNow} onChange={(e) => setRegenerateNow(e.target.checked)} />}
              label="Regenerar tasas inmediatamente al guardar"
            />
            <Button variant="contained" startIcon={<SaveIcon />} onClick={() => setConfirmOpen(true)} disabled={saving}>
              Guardar Márgenes
            </Button>
          </Stack>
        </Paper>

        {/* Profit Split */}
        <Paper sx={{ p: 3, borderLeft: "4px solid #2563EB" }}>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
            <HistoryIcon sx={{ color: "#2563EB" }} />
            <Typography variant="h6" sx={{ fontWeight: 700 }}>Distribución de Profit (Splits)</Typography>
          </Stack>

          <Stack direction="row" spacing={3} sx={{ mb: 3 }}>
            <TextField
              label="Operador (con Sponsor) (%)"
              value={opWithSponsor}
              onChange={(e) => setOpWithSponsor(e.target.value)}
              helperText="Lo que recibe el op si tiene sponsor"
              size="small"
              fullWidth
            />
            <TextField
              label="Sponsor (%)"
              value={sponsorPct}
              onChange={(e) => setSponsorPct(e.target.value)}
              helperText="Comisión para el sponsor"
              size="small"
              fullWidth
            />
            <TextField
              label="Operador Solo (%)"
              value={opSolo}
              onChange={(e) => setOpSolo(e.target.value)}
              helperText="Lo que recibe el op si NO tiene sponsor"
              size="small"
              fullWidth
            />
          </Stack>
          <Box sx={{ textAlign: "right" }}>
            <Button variant="contained" onClick={saveProfitSplit} disabled={saving}>
              Guardar Splits
            </Button>
          </Box>
        </Paper>

        {/* 💵 Entrega en Efectivo USD */}
        <CashDeliveryPanel saving={saving} setSaving={setSaving} setError={setError} setSuccess={setSuccess} />

      </Stack>

      {/* Confirm Dialog */}
      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)}>
        <DialogTitle>¿Confirmar cambios?</DialogTitle>
        <DialogContent>
          <Typography>
            Se actualizarán los márgenes globales en la base de datos.
            {regenerateNow && " Además, se iniciará el proceso de regeneración de tasas."}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)}>Cancelar</Button>
          <Button onClick={saveMargins} variant="contained" color="primary">Confirmar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
