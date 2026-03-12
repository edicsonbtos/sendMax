'use client';

import * as React from "react";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stack,
  MenuItem,
  CircularProgress,
  Alert,
  Tooltip,
  Chip,
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

interface CommissionRoute {
  id: number;
  origin: string;
  dest: string;
  margin_percent: string;
  is_active: boolean;
  notes?: string;
}

export default function RoutesPage() {
  const { token } = useAuth();
  const [routes, setRoutes] = React.useState<CommissionRoute[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Dialog state
  const [open, setOpen] = React.useState(false);
  const [editId, setEditId] = React.useState<number | null>(null);
  const [editOrigin, setEditOrigin] = React.useState("USA");
  const [editDest, setEditDest] = React.useState("VENEZUELA");
  const [editPercent, setEditPercent] = React.useState("");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<CommissionRoute[]>('/admin/settings/routes');
      setRoutes(res.data || []);
    } catch (e: any) {
      setError(e.message || "Error cargando rutas");
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (token) load();
  }, [token]);

  const handleAdd = () => {
    setEditId(null);
    setEditOrigin("USA");
    setEditDest("VENEZUELA");
    setEditPercent("");
    setOpen(true);
  };

  const handleEdit = (r: CommissionRoute) => {
    setEditId(r.id);
    setEditOrigin(r.origin);
    setEditDest(r.dest);
    setEditPercent(r.margin_percent);
    setOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm("¿Eliminar esta ruta de comisión?")) return;
    setSaving(true);
    try {
      await apiRequest(`/admin/settings/routes/${id}`, { method: 'DELETE' });
      load();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setSaving(true);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        origin: editOrigin,
        dest: editDest,
        margin_percent: parseFloat(editPercent)
      };

      if (editId) {
        await apiPut(`/admin/settings/routes/${editId}`, payload);
      } else {
        await apiRequest('/admin/settings/routes', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
      }
      setOpen(false);
      load();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box sx={{ p: 4 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Rutas de Comisión</Typography>
          <Typography variant="body2" color="text.secondary">Overrides específicos por corredor (Ej: USA a VE)</Typography>
        </Box>
        <Stack direction="row" spacing={2}>
          <IconButton onClick={load} disabled={loading}><RefreshIcon /></IconButton>
          <Button variant="contained" startIcon={<AddIcon />} onClick={handleAdd}>Nueva Ruta</Button>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}><CircularProgress /></Box>
      ) : (
        <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid #E2E8F0', borderRadius: 2 }}>
          <Table>
            <TableHead sx={{ bgcolor: '#F8FAFC' }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Origen</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Destino</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Margen Override</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="center">Estado</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {routes.length === 0 ? (
                <TableRow><TableCell colSpan={5} align="center" sx={{ py: 4 }}>No hay rutas configuradas. Se usarán los márgenes globales.</TableCell></TableRow>
              ) : (
                routes.map((r) => (
                  <TableRow key={r.id} hover>
                    <TableCell>{r.origin}</TableCell>
                    <TableCell>{r.dest}</TableCell>
                    <TableCell sx={{ fontWeight: 700, color: '#16A34A' }}>{r.margin_percent}%</TableCell>
                    <TableCell align="center">
                      <Chip 
                        label={r.is_active ? "Activa" : "Inactiva"} 
                        size="small" 
                        color={r.is_active ? "success" : "default"}
                        variant={r.is_active ? "filled" : "outlined"}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => handleEdit(r)}><EditIcon fontSize="small" /></IconButton>
                      <IconButton size="small" color="error" onClick={() => handleDelete(r.id)}><DeleteIcon fontSize="small" /></IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle sx={{ fontWeight: 700 }}>{editId ? "Editar Ruta" : "Nueva Ruta de Comisión"}</DialogTitle>
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
