"use client";

import * as React from "react";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Stack,
  Switch,
  FormControlLabel,
  Divider,
  Chip,
  Tooltip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Slider,
  InputAdornment,
} from "@mui/material";
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  TrendingUp as MarginIcon,
  CurrencyExchange as P2PIcon,
  Speed as EngineIcon,
  History as HistoryIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Info as InfoIcon,
} from "@mui/icons-material";
import { useAuth } from "@/components/AuthProvider";
import { apiRequest } from "@/lib/api";

/* ============ Types ============ */
type SettingsItem = {
  key: string;
  value_json: Record<string, unknown>;
  updated_at?: string | null;
  updated_by?: string | null;
};

/* ============ Helpers ============ */
function findSetting(items: SettingsItem[], key: string) {
  return items.find((x) => x.key === key)?.value_json ?? null;
}

function findUpdatedAt(items: SettingsItem[], key: string): string | null {
  return items.find((x) => x.key === key)?.updated_at ?? null;
}

async function putSetting(key: string, value_json: Record<string, unknown>) {
  return apiRequest(`/admin/settings/${encodeURIComponent(key)}`, {
    method: "PUT",
    body: JSON.stringify({ value_json }),
  });
}

function toNum(label: string, v: string): number {
  const n = Number(String(v).replace(",", "."));
  if (!Number.isFinite(n)) throw new Error(`${label}: debe ser numerico`);
  return n;
}

function marginStatus(val: string): { color: string; label: string; severity: "success" | "warning" | "error" } {
  const n = Number(val);
  if (isNaN(n)) return { color: "#DC2626", label: "Invalido", severity: "error" };
  if (n < 0) return { color: "#DC2626", label: "Negativo", severity: "error" };
  if (n === 0) return { color: "#F59E0B", label: "Sin margen", severity: "warning" };
  if (n > 20) return { color: "#F59E0B", label: "Muy alto", severity: "warning" };
  return { color: "#16A34A", label: "OK", severity: "success" };
}

function formatDate(iso: string | null): string {
  if (!iso) return "Nunca";
  return new Date(iso).toLocaleString("es-VE", {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

const CURRENCY_LABELS: Record<string, string> = {
  VES: "Venezuela (Bs)", COP: "Colombia (COP)", CLP: "Chile (CLP)",
  PEN: "Peru (PEN)", ARS: "Argentina (ARS)", MXN: "Mexico (MXN)", USD: "USA (USD)",
};

/* ============ Component ============ */
export default function SettingsPage() {
  const { apiKey } = useAuth();
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [lastUpdates, setLastUpdates] = React.useState<Record<string, string | null>>({});

  // Margins
  const [marginDefault, setMarginDefault] = React.useState("10");
  const [marginDestVenez, setMarginDestVenez] = React.useState("6");
  const [marginRouteUsaVenez, setMarginRouteUsaVenez] = React.useState("10");

  // Pricing engine
  const [fluctuationThreshold, setFluctuationThreshold] = React.useState("3");

  // Binance P2P
  const [p2pRows, setP2pRows] = React.useState("10");
  const [p2pRequireMerchant, setP2pRequireMerchant] = React.useState(true);
  const [p2pRef, setP2pRef] = React.useState<Record<string, number>>({
    VES: 39000, COP: 150000, CLP: 95000, PEN: 150, ARS: 180000, MXN: 1500, USD: 130,
  });

  // Dirty tracking
  const [originalValues, setOriginalValues] = React.useState<string>("");
  const currentValues = React.useMemo(() =>
    JSON.stringify({ marginDefault, marginDestVenez, marginRouteUsaVenez, fluctuationThreshold, p2pRows, p2pRequireMerchant, p2pRef }),
    [marginDefault, marginDestVenez, marginRouteUsaVenez, fluctuationThreshold, p2pRows, p2pRequireMerchant, p2pRef]
  );
  const isDirty = originalValues !== "" && originalValues !== currentValues;

  async function load() {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await apiRequest<{ items: SettingsItem[] }>("/admin/settings");
      const items = res.items ?? [];

      const md = findSetting(items, "margin_default");
      const mv = findSetting(items, "margin_dest_venez");
      const musv = findSetting(items, "margin_route_usa_venez");
      const ft = findSetting(items, "pricing_fluctuation_threshold");
      const rows = findSetting(items, "p2p_rows");
      const rm = findSetting(items, "p2p_require_merchant");
      const ref = findSetting(items, "p2p_reference_amounts");

      const mdVal = md?.percent != null ? String(Number(md.percent) * 100) : "10";
      const mvVal = mv?.percent != null ? String(Number(mv.percent) * 100) : "6";
      const musvVal = musv?.percent != null ? String(Number(musv.percent) * 100) : "10";
      const ftVal = ft?.percent != null ? String(Number(ft.percent) * 100) : "3";
      const rowsVal = rows?.rows != null ? String(rows.rows) : "10";
      const rmVal = rm?.enabled != null ? Boolean(rm.enabled) : true;
      const refVal = ref && typeof ref === "object" && !Array.isArray(ref) ? (ref as Record<string, number>) : p2pRef;

      setMarginDefault(mdVal);
      setMarginDestVenez(mvVal);
      setMarginRouteUsaVenez(musvVal);
      setFluctuationThreshold(ftVal);
      setP2pRows(rowsVal);
      setP2pRequireMerchant(rmVal);
      setP2pRef(refVal);

      setOriginalValues(JSON.stringify({
        marginDefault: mdVal, marginDestVenez: mvVal, marginRouteUsaVenez: musvVal,
        fluctuationThreshold: ftVal, p2pRows: rowsVal, p2pRequireMerchant: rmVal, p2pRef: refVal,
      }));

      setLastUpdates({
        margin_default: findUpdatedAt(items, "margin_default"),
        margin_dest_venez: findUpdatedAt(items, "margin_dest_venez"),
        margin_route_usa_venez: findUpdatedAt(items, "margin_route_usa_venez"),
        pricing_fluctuation_threshold: findUpdatedAt(items, "pricing_fluctuation_threshold"),
        p2p_rows: findUpdatedAt(items, "p2p_rows"),
        p2p_require_merchant: findUpdatedAt(items, "p2p_require_merchant"),
        p2p_reference_amounts: findUpdatedAt(items, "p2p_reference_amounts"),
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error cargando ajustes");
    } finally {
      setLoading(false);
    }
  }

  async function saveAll() {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const mdNum = toNum("Margen general", marginDefault);
      const mvNum = toNum("Margen destino Venezuela", marginDestVenez);
      const musvNum = toNum("Margen USA-Venezuela", marginRouteUsaVenez);
      const ftNum = toNum("Umbral volatilidad", fluctuationThreshold);
      const rowsNum = Math.trunc(toNum("Ordenes a revisar", p2pRows));

      if (mdNum < 0 || mdNum > 50) throw new Error("Margen general debe estar entre 0% y 50%");
      if (mvNum < 0 || mvNum > 50) throw new Error("Margen Venezuela debe estar entre 0% y 50%");
      if (musvNum < 0 || musvNum > 50) throw new Error("Margen USA-VE debe estar entre 0% y 50%");
      if (ftNum < 0 || ftNum > 20) throw new Error("Umbral volatilidad debe estar entre 0% y 20%");
      if (rowsNum < 1 || rowsNum > 50) throw new Error("Ordenes P2P debe estar entre 1 y 50");

      await putSetting("margin_default", { percent: mdNum / 100 });
      await putSetting("margin_dest_venez", { percent: mvNum / 100 });
      await putSetting("margin_route_usa_venez", { percent: musvNum / 100 });
      await putSetting("pricing_fluctuation_threshold", { percent: ftNum / 100 });
      await putSetting("p2p_rows", { rows: rowsNum });
      await putSetting("p2p_require_merchant", { enabled: Boolean(p2pRequireMerchant) });
      await putSetting("p2p_reference_amounts", p2pRef);

      setSuccess("Todos los ajustes guardados correctamente");
      setConfirmOpen(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error guardando ajustes");
    } finally {
      setSaving(false);
    }
  }

  React.useEffect(() => { if (apiKey) load(); }, [apiKey]);

  const marginFields = [
    { key: "margin_default", label: "Margen general", value: marginDefault, setter: setMarginDefault, helper: "Aplicado a todas las rutas por defecto" },
    { key: "margin_dest_venez", label: "Margen destino Venezuela", value: marginDestVenez, setter: setMarginDestVenez, helper: "Override para envios hacia Venezuela" },
    { key: "margin_route_usa_venez", label: "Margen USA a Venezuela", value: marginRouteUsaVenez, setter: setMarginRouteUsaVenez, helper: "Override especifico USA -> Venezuela" },
  ];
  return (
    <Box className="fade-in">
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>Configuracion</Typography>
          <Typography variant="body2" sx={{ color: "#64748B", mt: 0.5 }}>
            Margenes, motor de tasas y parametros Binance P2P
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          {isDirty && (
            <Chip icon={<WarningIcon sx={{ fontSize: 16 }} />} label="Cambios sin guardar" size="small" sx={{ backgroundColor: "#FEF3C7", color: "#92400E", fontWeight: 700 }} />
          )}
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={load} disabled={loading || saving} size="small">
            Recargar
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={() => setConfirmOpen(true)}
            disabled={loading || saving || !isDirty}
            size="small"
          >
            Guardar cambios
          </Button>
        </Stack>
      </Stack>

      {(loading || saving) && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress sx={{ color: "#4B2E83" }} />
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      {!loading && (
        <Stack spacing={3}>
          {/* Margenes */}
          <Paper sx={{ p: 3, borderLeft: "4px solid #4B2E83" }}>
            <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
              <Box sx={{ backgroundColor: "#4B2E8312", borderRadius: "12px", p: 1, display: "flex" }}>
                <MarginIcon sx={{ color: "#4B2E83", fontSize: 24 }} />
              </Box>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>Margenes (Ganancia)</Typography>
                <Typography variant="caption" sx={{ color: "#64748B" }}>Porcentajes aplicados a la tasa final del cliente</Typography>
              </Box>
            </Stack>

            <Stack spacing={2.5}>
              {marginFields.map((f) => {
                const status = marginStatus(f.value);
                return (
                  <Box key={f.key}>
                    <Stack direction="row" spacing={2} alignItems="flex-start">
                      <TextField
                        label={f.label}
                        value={f.value}
                        onChange={(e) => f.setter(e.target.value)}
                        disabled={loading || saving}
                        sx={{ flex: 1, maxWidth: 300 }}
                        size="small"
                        InputProps={{
                          endAdornment: <InputAdornment position="end">%</InputAdornment>,
                        }}
                        helperText={f.helper}
                      />
                      <Chip
                        label={status.label}
                        size="small"
                        sx={{ mt: 1, fontWeight: 700, height: 24, backgroundColor: `${status.color}15`, color: status.color }}
                      />
                      <Tooltip title={`Ultima actualizacion: ${formatDate(lastUpdates[f.key] ?? null)}`}>
                        <IconButton size="small" sx={{ mt: 0.5 }}>
                          <HistoryIcon sx={{ fontSize: 18, color: "#94A3B8" }} />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                    {Number(f.value) > 0 && Number(f.value) <= 50 && (
                      <Slider
                        value={Number(f.value) || 0}
                        onChange={(_, v) => f.setter(String(v))}
                        min={0}
                        max={30}
                        step={0.5}
                        disabled={loading || saving}
                        sx={{ maxWidth: 300, ml: 0, mt: 0.5, color: "#4B2E83", "& .MuiSlider-thumb": { width: 16, height: 16 } }}
                        valueLabelDisplay="auto"
                        valueLabelFormat={(v) => `${v}%`}
                      />
                    )}
                  </Box>
                );
              })}
            </Stack>

            {/* Preview */}
            <Divider sx={{ my: 2 }} />
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
              <InfoIcon sx={{ fontSize: 16, color: "#64748B" }} />
              <Typography variant="caption" sx={{ color: "#64748B", fontWeight: 600 }}>
                Preview: Si tasa base es $1.00, el cliente ve:
              </Typography>
            </Stack>
            <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", gap: 1 }}>
              {marginFields.map((f) => {
                const pct = Number(f.value) || 0;
                const clientRate = (1 * (1 - pct / 100)).toFixed(4);
                return (
                  <Chip
                    key={f.key}
                    label={`${f.label.replace("Margen ", "")}: $${clientRate}`}
                    size="small"
                    variant="outlined"
                    sx={{ fontWeight: 600, fontFamily: "monospace" }}
                  />
                );
              })}
            </Stack>
          </Paper>

          {/* Motor de tasas */}
          <Paper sx={{ p: 3, borderLeft: "4px solid #2563EB" }}>
            <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
              <Box sx={{ backgroundColor: "#2563EB12", borderRadius: "12px", p: 1, display: "flex" }}>
                <EngineIcon sx={{ color: "#2563EB", fontSize: 24 }} />
              </Box>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>Motor de tasas</Typography>
                <Typography variant="caption" sx={{ color: "#64748B" }}>Controla cuando se recalculan tasas por cambios del mercado</Typography>
              </Box>
            </Stack>

            <Stack direction="row" spacing={2} alignItems="flex-start">
              <TextField
                label="Umbral de volatilidad"
                value={fluctuationThreshold}
                onChange={(e) => setFluctuationThreshold(e.target.value)}
                disabled={loading || saving}
                sx={{ maxWidth: 300 }}
                size="small"
                InputProps={{
                  endAdornment: <InputAdornment position="end">%</InputAdornment>,
                }}
                helperText="Si el precio P2P cambia mas de este %, se recalcula la tasa"
              />
              <Chip
                label={marginStatus(fluctuationThreshold).label}
                size="small"
                sx={{ mt: 1, fontWeight: 700, height: 24, backgroundColor: `${marginStatus(fluctuationThreshold).color}15`, color: marginStatus(fluctuationThreshold).color }}
              />
              <Tooltip title={`Ultima actualizacion: ${formatDate(lastUpdates.pricing_fluctuation_threshold ?? null)}`}>
                <IconButton size="small" sx={{ mt: 0.5 }}>
                  <HistoryIcon sx={{ fontSize: 18, color: "#94A3B8" }} />
                </IconButton>
              </Tooltip>
            </Stack>

            <Slider
              value={Number(fluctuationThreshold) || 0}
              onChange={(_, v) => setFluctuationThreshold(String(v))}
              min={0}
              max={10}
              step={0.5}
              disabled={loading || saving}
              sx={{ maxWidth: 300, mt: 0.5, color: "#2563EB", "& .MuiSlider-thumb": { width: 16, height: 16 } }}
              valueLabelDisplay="auto"
              valueLabelFormat={(v) => `${v}%`}
            />
          </Paper>

          {/* Binance P2P */}
          <Paper sx={{ p: 3, borderLeft: "4px solid #F59E0B" }}>
            <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
              <Box sx={{ backgroundColor: "#F59E0B12", borderRadius: "12px", p: 1, display: "flex" }}>
                <P2PIcon sx={{ color: "#F59E0B", fontSize: 24 }} />
              </Box>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>Binance P2P</Typography>
                <Typography variant="caption" sx={{ color: "#64748B" }}>Parametros para seleccionar el mejor precio de referencia</Typography>
              </Box>
            </Stack>

            <Stack direction="row" spacing={3} alignItems="flex-start" sx={{ mb: 3 }}>
              <TextField
                label="Ordenes a revisar"
                value={p2pRows}
                onChange={(e) => setP2pRows(e.target.value)}
                disabled={loading || saving}
                sx={{ maxWidth: 200 }}
                size="small"
                helperText="Cuantas ofertas P2P analizar (1-50)"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={p2pRequireMerchant}
                    onChange={(e) => setP2pRequireMerchant(e.target.checked)}
                    disabled={loading || saving}
                    sx={{ "& .MuiSwitch-switchBase.Mui-checked": { color: "#F59E0B" }, "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track": { backgroundColor: "#F59E0B" } }}
                  />
                }
                label={
                  <Stack>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>Solo comerciantes verificados</Typography>
                    <Typography variant="caption" sx={{ color: "#64748B" }}>Filtra ofertas de merchants Binance</Typography>
                  </Stack>
                }
              />
            </Stack>

            <Divider sx={{ mb: 2 }} />

            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Montos de referencia por moneda</Typography>
              <Tooltip title="Se usa para filtrar ofertas por un monto tipico y evitar precios irreales">
                <InfoIcon sx={{ fontSize: 16, color: "#94A3B8" }} />
              </Tooltip>
              <Tooltip title={`Ultima actualizacion: ${formatDate(lastUpdates.p2p_reference_amounts ?? null)}`}>
                <IconButton size="small">
                  <HistoryIcon sx={{ fontSize: 16, color: "#94A3B8" }} />
                </IconButton>
              </Tooltip>
            </Stack>

            <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", gap: 2 }}>
              {Object.entries(p2pRef).sort(([a], [b]) => a.localeCompare(b)).map(([fiat, amt]) => (
                <TextField
                  key={fiat}
                  label={CURRENCY_LABELS[fiat] || fiat}
                  value={String(amt)}
                  onChange={(e) => {
                    const n = Number(String(e.target.value).replace(",", "."));
                    setP2pRef((prev) => ({ ...prev, [fiat]: Number.isFinite(n) ? n : prev[fiat] }));
                  }}
                  disabled={loading || saving}
                  size="small"
                  sx={{ width: 160 }}
                  InputProps={{
                    endAdornment: <InputAdornment position="end">{fiat}</InputAdornment>,
                  }}
                />
              ))}
            </Stack>
          </Paper>
        </Stack>
      )}

      {/* Confirm Dialog */}
      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Confirmar cambios</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            Los cambios en margenes afectan INMEDIATAMENTE las tasas que ven los clientes.
          </Alert>
          <Typography variant="body2" sx={{ color: "#64748B" }}>
            Se guardaran los nuevos valores de margenes, motor de tasas y parametros P2P.
            Esta accion queda registrada en el audit log.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)} disabled={saving}>Cancelar</Button>
          <Button
            variant="contained"
            onClick={saveAll}
            disabled={saving}
            startIcon={saving ? <CircularProgress size={16} /> : <CheckIcon />}
            sx={{ backgroundColor: "#4B2E83" }}
          >
            {saving ? "Guardando..." : "Confirmar y guardar"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}