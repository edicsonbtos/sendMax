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
  GridLegacy as Grid,
  } from "@mui/material";


import { apiRequest } from "@/lib/api";

type SettingsItem = {
  key: string;
  value_json: any;
  updated_at?: string | null;
};

function findSetting(items: SettingsItem[], key: string) {
  return items.find((x) => x.key === key)?.value_json ?? null;
}

async function putSetting(key: string, value_json: any) {
  return apiRequest(`/admin/settings/${encodeURIComponent(key)}`, {
    method: "PUT",
    body: JSON.stringify({ value_json }),
  });
}

export default function SettingsPage() {
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);

  // Margins (UI en % humano)
  const [marginDefault, setMarginDefault] = React.useState("10");
  const [marginDestVenez, setMarginDestVenez] = React.useState("6");
  const [marginRouteUsaVenez, setMarginRouteUsaVenez] = React.useState("10");

  // Pricing engine (UI en % humano)
  const [fluctuationThreshold, setFluctuationThreshold] = React.useState("3");

  // Binance P2P
  const [p2pRows, setP2pRows] = React.useState("10");
  const [p2pRequireMerchant, setP2pRequireMerchant] = React.useState(true);

  const [p2pRef, setP2pRef] = React.useState<Record<string, number>>({
    VES: 39000,
    COP: 150000,
    CLP: 95000,
    PEN: 150,
    ARS: 180000,
    MXN: 1500,
    USD: 130,
  });

  async function load() {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await apiRequest<{ items: SettingsItem[] }>("/admin/settings");
      const items = res.items ?? [];

      const md = findSetting(items, "margin_default")?.percent;
      const mv = findSetting(items, "margin_dest_venez")?.percent;
      const musv = findSetting(items, "margin_route_usa_venez")?.percent;

      if (md !== undefined && md !== null) setMarginDefault(String(Number(md) * 100));
      if (mv !== undefined && mv !== null) setMarginDestVenez(String(Number(mv) * 100));
      if (musv !== undefined && musv !== null) setMarginRouteUsaVenez(String(Number(musv) * 100));

      const ft = findSetting(items, "pricing_fluctuation_threshold")?.percent;
      if (ft !== undefined && ft !== null) setFluctuationThreshold(String(Number(ft) * 100));

      const r = findSetting(items, "p2p_rows")?.rows;
      if (r !== undefined && r !== null) setP2pRows(String(r));

      const rm = findSetting(items, "p2p_require_merchant")?.enabled;
      if (rm !== undefined && rm !== null) setP2pRequireMerchant(Boolean(rm));

      const ref = findSetting(items, "p2p_reference_amounts");
      if (ref && typeof ref === "object") setP2pRef(ref);
    } catch (e: any) {
      setError(e?.message ?? "Error cargando ajustes");
    } finally {
      setLoading(false);
    }
  }

  function toNum(label: string, v: string) {
    const n = Number(String(v).replace(",", "."));
    if (!Number.isFinite(n)) throw new Error(`${label}: debe ser numérico`);
    return n;
  }

  async function saveAll() {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await putSetting("margin_default", { percent: toNum("Margen general (%)", marginDefault) / 100 });
      await putSetting("margin_dest_venez", { percent: toNum("Margen destino Venezuela (%)", marginDestVenez) / 100 });
      await putSetting("margin_route_usa_venez", { percent: toNum("Margen USA → Venezuela (%)", marginRouteUsaVenez) / 100 });

      await putSetting("pricing_fluctuation_threshold", { percent: toNum("Umbral de volatilidad (%)", fluctuationThreshold) / 100 });

      await putSetting("p2p_rows", { rows: Math.trunc(toNum("Órdenes a revisar", p2pRows)) });
      await putSetting("p2p_require_merchant", { enabled: Boolean(p2pRequireMerchant) });
      await putSetting("p2p_reference_amounts", p2pRef);

      setSuccess("Guardado correctamente");
      await load();
    } catch (e: any) {
      console.error("SAVE_SETTINGS_ERROR", e);
      setError(e?.message ?? "Error guardando ajustes");
    } finally {
      setSaving(false);
    }
  }

  React.useEffect(() => {
    load();
  }, []);

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }} spacing={2}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 800 }}>
            Ajustes
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.5 }}>
            Configuración operativa (márgenes, Binance P2P y reglas del motor de tasas).
          </Typography>
        </Box>

        <Stack direction="row" spacing={1}>
          <Button variant="outlined" onClick={load} disabled={loading || saving}>
            Recargar
          </Button>
          <Button variant="contained" onClick={saveAll} disabled={loading || saving}>
            Guardar cambios
          </Button>
        </Stack>
      </Stack>

      {(loading || saving) && (
        <Paper sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <CircularProgress size={18} />
            <Typography variant="body2">{loading ? "Cargando..." : "Guardando..."}</Typography>
          </Box>
        </Paper>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      <Grid container spacing={2}>
        {/* Márgenes */}
        <Grid xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>
              Márgenes (Ganancia)
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary", mb: 2 }}>
              Porcentajes aplicados a la tasa final que ve el cliente.
            </Typography>

            <Grid container spacing={2}>
              <Grid xs={12}>
                <TextField
                  label="Margen general (%)"
                  value={marginDefault}
                  onChange={(e) => setMarginDefault(e.target.value)}
                  disabled={loading || saving}
                  fullWidth
                  helperText="Ej: 10"
                />
              </Grid>

              <Grid xs={12}>
                <TextField
                  label="Margen destino Venezuela (%)"
                  value={marginDestVenez}
                  onChange={(e) => setMarginDestVenez(e.target.value)}
                  disabled={loading || saving}
                  fullWidth
                  helperText="Ej: 6"
                />
              </Grid>

              <Grid xs={12}>
                <TextField
                  label="Margen USA → Venezuela (%)"
                  value={marginRouteUsaVenez}
                  onChange={(e) => setMarginRouteUsaVenez(e.target.value)}
                  disabled={loading || saving}
                  fullWidth
                  helperText="Ej: 10"
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Motor de tasas */}
        <Grid xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>
              Motor de tasas
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary", mb: 2 }}>
              Controla cuándo se recalculan tasas por cambios bruscos del mercado.
            </Typography>

            <TextField
              label="Umbral de volatilidad (%)"
              value={fluctuationThreshold}
              onChange={(e) => setFluctuationThreshold(e.target.value)}
              disabled={loading || saving}
              fullWidth
              helperText="Ej: 3 (si cambia 3% o más, recalcula)"
            />
          </Paper>
        </Grid>

        {/* Binance P2P */}
        <Grid xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>
              Binance P2P
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary", mb: 2 }}>
              Parámetros para seleccionar el mejor precio de referencia.
            </Typography>

            <Grid container spacing={2} alignItems="center">
              <Grid xs={12} md={4}>
                <TextField
                  label="Órdenes a revisar"
                  value={p2pRows}
                  onChange={(e) => setP2pRows(e.target.value)}
                  disabled={loading || saving}
                  fullWidth
                  helperText="Ej: 10"
                />
              </Grid>

              <Grid xs={12} md={8}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={p2pRequireMerchant}
                      onChange={(e) => setP2pRequireMerchant(e.target.checked)}
                      disabled={loading || saving}
                    />
                  }
                  label="Usar solo comerciantes verificados (merchant)"
                />
              </Grid>
            </Grid>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
              Montos de referencia por moneda
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary", mb: 2 }}>
              Se usa para filtrar ofertas por un monto típico (evita precios irreales).
            </Typography>

            <Grid container spacing={2}>
              {Object.entries(p2pRef).map(([fiat, amt]) => (
                <Grid key={fiat} item xs={6} sm={4} md={2}>
                  <TextField
                    label={fiat}
                    value={String(amt)}
                    onChange={(e) => {
                      const n = Number(String(e.target.value).replace(",", "."));
                      setP2pRef((prev) => ({ ...prev, [fiat]: Number.isFinite(n) ? n : prev[fiat] }));
                    }}
                    disabled={loading || saving}
                    fullWidth
                    size="small"
                  />
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
