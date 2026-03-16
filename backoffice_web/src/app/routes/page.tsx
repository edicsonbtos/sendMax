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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TableContainer,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  MenuItem,
} from "@mui/material";
import {
  Refresh as RefreshIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
} from "@mui/icons-material";
import { useAuth } from "@/components/AuthProvider";
import { apiGet, apiPut, apiRequest } from "@/lib/api";

const COUNTRIES = [
  "USA", "CHILE", "PERU", "COLOMBIA", "VENEZUELA", "MEXICO", "ARGENTINA"
];

interface RouteCommissions {
  [key: string]: number;
}

export default function RoutesPage() {
  const { token } = useAuth();
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);

  const [routes, setRoutes] = React.useState<RouteCommissions>({});
  const [open, setOpen] = React.useState(false);

  const [editOrigin, setEditOrigin] = React.useState("CHILE");
  const [editDest, setEditDest] = React.useState("VENEZUELA");
  const [editPercent, setEditPercent] = React.useState("2");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<{ routes?: RouteCommissions }>("/api/v1/config/commissions");
      setRoutes(res.routes || {});
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error cargando rutas");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const routeKey = `${editOrigin.toUpperCase()}_${editDest.toUpperCase()}`;
      const percent = Number(editPercent) / 100;

      if (isNaN(percent) || percent < 0 || percent > 0.5) {
        throw new Error("Porcentaje inválido (0-50%)");
      }

      await apiPut("/api/v1/config/commission/route", {
        route: routeKey,
        percent: percent,
      });

      setSuccess(`Ruta ${routeKey} actualizada`);
      setOpen(false);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error guardando ruta");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(routeKey: string) {
    if (!confirm(`¿Eliminar el margen específico para ${routeKey}? Se usará el margen por defecto.`)) return;
    setSaving(true);
    try {
      await apiRequest(`/api/v1/config/commission/route/${routeKey}`, {
        method: "DELETE",
      });
      setSuccess(`Ruta ${routeKey} eliminada`);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error eliminando ruta");
    } finally {
      setSaving(false);
    }
  }

  React.useEffect(() => { if (token) load(); }, [token]);

  if (loading) return <Box sx={{ display: "flex", justifyContent: "center", py: 10 }}><CircularProgress /></Box>;

  const routeList = Object.entries(routes).sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <Box className="fade-in">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>Rutas de Comisión</Typography>
          <Typography variant="body2" color="text.secondary">Configuración granular por origen y destino (Overriding global)</Typography>
        </Box>
        <Stack direction="row" spacing={2}>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={load}>Recargar</Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpen(true)}>Nueva Ruta</Button>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 3 }}>{success}</Alert>}

      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Ruta (Origen_Destino)</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Margen (%)</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {routeList.length === 0 ? (
                <TableRow><TableCell colSpan={3} align="center">No hay rutas específicas configuradas</TableCell></TableRow>
              ) : (
                routeList.map(([key, val]) => (
                  <TableRow key={key}>
                    <TableCell sx={{ fontWeight: 600, fontFamily: "monospace" }}>{key}</TableCell>
                    <TableCell>{(val * 100).toFixed(2)}%</TableCell>
                    <TableCell align="right">
                      <IconButton size="small" color="error" onClick={() => handleDelete(key)} disabled={saving}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" onClick={() => {
                        const [o, d] = key.split("_");
                        setEditOrigin(o);
                        setEditDest(d);
                        setEditPercent(String(val * 100));
                        setOpen(true);
                      }}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>{editPercent ? "Editar Ruta" : "Nueva Ruta"}</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1 }}>
            <TextField
              select
              label="País Origen"
              value={editOrigin}
              onChange={(e) => setEditOrigin(e.target.value)}
              fullWidth
            >
              {COUNTRIES.map((c) => <MenuItem key={c} value={c}>{c}</MenuItem>)}
            </TextField>
            <TextField
              select
              label="País Destino"
              value={editDest}
              onChange={(e) => setEditDest(e.target.value)}
              fullWidth
            >
              {COUNTRIES.map((c) => <MenuItem key={c} value={c}>{c}</MenuItem>)}
            </TextField>
            <TextField
              label="Margen (%)"
              value={editPercent}
              onChange={(e) => setEditPercent(e.target.value)}
              InputProps={{ endAdornment: "%" }}
              fullWidth
              helperText="Ej: 2.5 para 2.50%"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancelar</Button>
          <Button onClick={handleSave} variant="contained" disabled={saving}>Guardar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
