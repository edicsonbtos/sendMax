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
  Checkbox,
  FormControlLabel,
  Divider,
  Chip,
  Tooltip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TableContainer,
} from "@mui/material";
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  TrendingUp as MarginIcon,
  Speed as EngineIcon,
  History as HistoryIcon,
  CheckCircle as CheckIcon,
  Sync as SyncIcon,
  AttachMoney as CashIcon,
} from "@mui/icons-material";
import { useAuth } from "@/components/AuthProvider";
import { apiGet, apiPost, apiPut } from "@/lib/api";

/* ============ Types ============ */
interface RateVersion {
  id: number;
  kind: string;
  reason: string | null;
  created_at: string;
  effective_from: string;
  is_active: boolean;
}

interface CommissionsConfig {
  margin_default?: { percent: number };
  margin_dest_venez?: { percent: number };
  margin_route_usa_venez?: { percent: number };
  profit_split?: {
    operator_with_sponsor: number;
    sponsor: number;
    operator_solo: number;
  };
}

/* ============ Helpers ============ */
function toNum(label: string, v: string): number {
  const n = Number(String(v).replace(",", "."));
  if (!Number.isFinite(n)) throw new Error(`${label}: debe ser numerico`);
  return n;
}

function formatDate(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("es-VE", {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

/* ============ CashDeliveryPanel ============ */
interface CashDeliveryPanelProps {
  saving: boolean;
  setSaving: (v: boolean) => void;
  setError: (v: string | null) => void;
  setSuccess: (v: string | null) => void;
}

function CashDeliveryPanel({ saving, setSaving, setError, setSuccess }: CashDeliveryPanelProps) {
  const [zelleCost, setZelleCost] = React.useState("1.03");
  const [marginZelle, setMarginZelle] = React.useState("12");
  const [marginGeneral, setMarginGeneral] = React.useState("10");
  const [loaded, setLoaded] = React.useState(false);

  React.useEffect(() => {
    apiGet<{ value_json?: { zelle_usdt_cost?: number; margin_cash_zelle?: number; margin_cash_general?: number } }>("/settings/cash_delivery")
      .then((res) => {
        const v = res?.value_json;
        if (v) {
          if (v.zelle_usdt_cost !== undefined) setZelleCost(String(v.zelle_usdt_cost));
          if (v.margin_cash_zelle !== undefined) setMarginZelle(String(v.margin_cash_zelle));
          if (v.margin_cash_general !== undefined) setMarginGeneral(String(v.margin_cash_general));
        }
        setLoaded(true);
      })
      .catch(() => setLoaded(true)); // use defaults if not yet in DB
  }, []);

  async function save() {
    const cost = Number(String(zelleCost).replace(",", "."));
    const mz = Number(String(marginZelle).replace(",", "."));
    const mg = Number(String(marginGeneral).replace(",", "."));

    if (!Number.isFinite(cost) || cost < 1.0 || cost > 2.0)
      return setError("Costo Zelle: debe estar entre 1.0 y 2.0");
    if (!Number.isFinite(mz) || mz < 0 || mz > 50)
      return setError("Margen Zelle: debe estar entre 0 y 50");
    if (!Number.isFinite(mg) || mg < 0 || mg > 50)
      return setError("Margen General: debe estar entre 0 y 50");

    setSaving(true);
    setError(null);
    try {
      await apiPut("/settings/cash_delivery", {
        value_json: {
          zelle_usdt_cost: cost,
          margin_cash_zelle: mz,
          margin_cash_general: mg,
        },
      });
      setSuccess("💵 Configuración de Efectivo USD guardada. Activa en el próximo ciclo de tasas (≤60s).");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error guardando configuración efectivo");
    } finally {
      setSaving(false);
    }
  }

  if (!loaded) return null;

  return (
    <Paper sx={{ p: 3, borderLeft: "4px solid #F59E0B" }}>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
        <CashIcon sx={{ color: "#F59E0B" }} />
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
            💵 Entrega en Efectivo USD (Venezuela)
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Ruta USA Zelle → Efectivo usa costo fijo. Otros países usan precio Binance.
          </Typography>
        </Box>
      </Stack>
      <Divider sx={{ mb: 2.5 }} />
      <Stack direction="row" spacing={3} sx={{ mb: 3 }}>
        <TextField
          label="Costo Zelle por 1 USDT"
          value={zelleCost}
          onChange={(e) => setZelleCost(e.target.value)}
          helperText="Ej: 1.03 = pagas 1.03 USD Zelle para recibir 1 USDT"
          size="small"
          fullWidth
          type="number"
          inputProps={{ step: "0.01", min: "1.0", max: "2.0" }}
        />
        <TextField
          label="Margen Zelle → Efectivo (%)"
          value={marginZelle}
          onChange={(e) => setMarginZelle(e.target.value)}
          helperText="Comisión para ruta USA(Zelle) → Efectivo USD"
          size="small"
          fullWidth
          InputProps={{ endAdornment: "%" }}
        />
        <TextField
          label="Margen General → Efectivo (%)"
          value={marginGeneral}
          onChange={(e) => setMarginGeneral(e.target.value)}
          helperText="Comisión para otras rutas (CLP, COP, etc.) → Efectivo"
          size="small"
          fullWidth
          InputProps={{ endAdornment: "%" }}
        />
      </Stack>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Typography variant="caption" color="text.secondary">
          Tasas activas en ≤60s tras guardar (cache automático)
        </Typography>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={save}
          disabled={saving}
          sx={{ backgroundColor: "#F59E0B", "&:hover": { backgroundColor: "#D97706" } }}
        >
          Guardar Efectivo USD
        </Button>
      </Stack>
    </Paper>
  );
}

/* ============ Component ============ */
export default function SettingsPage() {
  const { token } = useAuth();
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = React.useState(false);

  // Margins
  const [marginDefault, setMarginDefault] = React.useState("10");
  const [marginDestVenez, setMarginDestVenez] = React.useState("6");
  const [marginRouteUsaVenez, setMarginRouteUsaVenez] = React.useState("10");
  const [regenerateNow, setRegenerateNow] = React.useState(false);

  // Profit Split
  const [opWithSponsor, setOpWithSponsor] = React.useState("45");
  const [sponsorPct, setSponsorPct] = React.useState("10");
  const [opSolo, setOpSolo] = React.useState("50");

  // Rates info
  const [activeVersion, setActiveVersion] = React.useState<RateVersion | null>(null);
  const [history, setHistory] = React.useState<RateVersion[]>([]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [commRes, activeRes, historyRes] = await Promise.all([
        apiGet<CommissionsConfig>("/api/v1/config/commissions"),
        apiGet<{ ok: boolean; version?: RateVersion }>("/api/v1/rates/active"),
        apiGet<{ versions: RateVersion[] }>("/api/v1/rates/versions?limit=10"),
      ]);

      if (commRes) {
        setMarginDefault(String((commRes.margin_default?.percent ?? 0.1) * 100));
        setMarginDestVenez(String((commRes.margin_dest_venez?.percent ?? 0.06) * 100));
        setMarginRouteUsaVenez(String((commRes.margin_route_usa_venez?.percent ?? 0.1) * 100));

        if (commRes.profit_split) {
          setOpWithSponsor(String(commRes.profit_split.operator_with_sponsor * 100));
          setSponsorPct(String(commRes.profit_split.sponsor * 100));
          setOpSolo(String(commRes.profit_split.operator_solo * 100));
        }
      }

      if (activeRes?.ok) {
        setActiveVersion(activeRes.version || null);
      }
      setHistory(historyRes?.versions || []);

    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error cargando ajustes");
    } finally {
      setLoading(false);
    }
  }

  async function saveMargins() {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const md = toNum("Margen general", marginDefault) / 100;
      const mv = toNum("Margen Venezuela", marginDestVenez) / 100;
      const musv = toNum("Margen USA-VE", marginRouteUsaVenez) / 100;

      await apiPost("/api/v1/config/margins", {
        margin_default: md,
        margin_dest_venez: mv,
        margin_route_usa_venez: musv,
        regenerate: regenerateNow,
      });

      setSuccess("Márgenes guardados correctamente" + (regenerateNow ? " y tasas regeneradas" : ""));
      setConfirmOpen(false);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error guardando márgenes");
    } finally {
      setSaving(false);
    }
  }

  async function manualRegen() {
    if (!confirm("¿Seguro que quieres regenerar todas las tasas ahora?")) return;
    setSaving(true);
    try {
      await apiPost("/api/v1/rates/regenerate", {
        kind: "manual",
        reason: "Desde Settings UI",
        activate: true,
      });
      setSuccess("Tasas regeneradas exitosamente");
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error regenerando tasas");
    } finally {
      setSaving(false);
    }
  }

  async function saveProfitSplit() {
    setSaving(true);
    setError(null);
    try {
      const opws = toNum("Op con sponsor", opWithSponsor) / 100;
      const sp = toNum("Sponsor", sponsorPct) / 100;
      const ops = toNum("Op solo", opSolo) / 100;

      if (opws + sp > 1) throw new Error("La suma de Operador + Sponsor no puede superar el 100%");

      await apiPost("/api/v1/config/profit-split", {
        operator_with_sponsor: opws,
        sponsor: sp,
        operator_solo: ops,
      });
      setSuccess("Distribución de profit actualizada");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error guardando profit split");
    } finally {
      setSaving(false);
    }
  }

  React.useEffect(() => { if (token) load(); }, [token]);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 10 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box className="fade-in" sx={{ pb: 6 }}>
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
