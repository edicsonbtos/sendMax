"use client";

import React, { useEffect, useMemo, useState, useCallback } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Stack,
  Button,
  TextField,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Divider,
  Chip,
} from "@mui/material";
import {
  Refresh as RefreshIcon,
  Send as SendIcon,
  DeleteSweep as EmptyIcon,
  AccountBalance as BalanceIcon,
} from "@mui/icons-material";
import { useAuth } from "@/components/AuthProvider";
import { apiRequest } from "@/lib/api";

type WalletRow = {
  origin_country: string;
  fiat_currency: string;
  total_in: number;
  total_out: number;
  current_balance: number;
};

type CurrentBalancesResponse = { ok: boolean; items: WalletRow[] };

const FLAGS: Record<string, string> = {
  VENEZUELA: "🇻🇪",
  VE: "🇻🇪",
  PERU: "🇵🇪",
  CHILE: "🇨🇱",
  COLOMBIA: "🇨🇴",
  USA: "🇺🇸",
  ARGENTINA: "🇦🇷",
  MEXICO: "🇲🇽",
};

function flagFor(country: string) {
  const key = String(country || "").trim().toUpperCase();
  return FLAGS[key] || "🏦";
}

function money(n: number) {
  return (n || 0).toLocaleString("es-VE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

export default function OriginPage() {
  const { apiKey } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [rows, setRows] = useState<WalletRow[]>([]);
  const [success, setSuccess] = useState("");

  const [search, setSearch] = useState("");

  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<"withdraw" | "empty">("withdraw");
  const [selected, setSelected] = useState<WalletRow | null>(null);
  const [amount, setAmount] = useState<string>("");
  const [note, setNote] = useState<string>("");
  const [actionLoading, setActionLoading] = useState(false);

  const fetchCurrent = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await apiRequest<CurrentBalancesResponse>("/origin-wallets/current-balances");
      setRows(data.items || []);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error desconocido";
      setError(message);
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (apiKey) fetchCurrent();
  }, [apiKey, fetchCurrent]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) =>
      `${r.origin_country} ${r.fiat_currency}`.toLowerCase().includes(q)
    );
  }, [rows, search]);

  const totalBalance = useMemo(() => rows.reduce((s, r) => s + (r.current_balance || 0), 0), [rows]);

  function openWithdraw(r: WalletRow) {
    setDialogMode("withdraw");
    setSelected(r);
    setAmount("");
    setNote("");
    setSuccess("");
    setDialogOpen(true);
  }

  function openEmpty(r: WalletRow) {
    setDialogMode("empty");
    setSelected(r);
    setAmount("");
    setNote("Vaciar caja (paso a USDT empresa)");
    setSuccess("");
    setDialogOpen(true);
  }

  async function submitAction() {
    if (!selected) return;

    setActionLoading(true);
    setError("");
    setSuccess("");

    const day = todayISO(); // usamos hoy para registrar sweep

    try {
      if (dialogMode === "withdraw") {
        const n = Number(String(amount).replace(",", "."));
        if (!Number.isFinite(n) || n <= 0) throw new Error("Monto inválido");

        await apiRequest("/origin-wallets/withdraw", {
          method: "POST",
          body: JSON.stringify({
            day,
            origin_country: selected.origin_country,
            fiat_currency: selected.fiat_currency,
            amount_fiat: n,
            note: note || "Retiro",
          }),
        });

        setSuccess("Retiro registrado");
      } else {
        await apiRequest("/origin-wallets/empty", {
          method: "POST",
          body: JSON.stringify({
            day,
            origin_country: selected.origin_country,
            fiat_currency: selected.fiat_currency,
            note: note || "Vaciar caja",
          }),
        });

        setSuccess("Billetera vaciada (saldo en 0)");
      }

      setDialogOpen(false);
      await fetchCurrent();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error desconocido";
      setError(message);
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <Box className="fade-in">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>
            Billeteras Origen
          </Typography>
          <Typography variant="body2" sx={{ color: "#64748B", mt: 0.5 }}>
            Vista por billetera: saldo actual acumulado y acciones para retirar / vaciar.
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<RefreshIcon />} onClick={fetchCurrent} disabled={loading}>
          Actualizar
        </Button>
      </Stack>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 2.5 }}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="center">
            <TextField
              label="Buscar billetera (país o moneda)"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              size="small"
              sx={{ width: { xs: "100%", md: 380 } }}
            />
            <Box sx={{ flex: 1 }} />
            <Chip
              icon={<BalanceIcon />}
              label={`Saldo total (suma): ${money(totalBalance)}`}
              sx={{ backgroundColor: "#EFEAFF", color: "#4B2E83", fontWeight: 800 }}
            />
          </Stack>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess("")}>
          {success}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress sx={{ color: "#4B2E83" }} />
        </Box>
      ) : (
        <Card>
          <CardContent sx={{ p: 0 }}>
            <Box sx={{ p: 2.5 }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Billeteras
              </Typography>
              <Typography variant="body2" sx={{ color: "#64748B", mt: 0.25 }}>
                Acciones registran un sweep con fecha de hoy ({todayISO()}).
              </Typography>
            </Box>

            <Divider />

            <TableContainer sx={{ maxHeight: 640 }}>
              <Table stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>Billetera</TableCell>
                    <TableCell>Moneda</TableCell>
                    <TableCell align="right">Entradas (hist)</TableCell>
                    <TableCell align="right">Retiros (hist)</TableCell>
                    <TableCell align="right">Saldo actual</TableCell>
                    <TableCell align="center">Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filtered.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align="center" sx={{ py: 6 }}>
                        <Typography variant="body2" color="text.secondary">
                          No hay billeteras para mostrar
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    filtered.map((r, idx) => {
                      const okZero = Math.abs(r.current_balance || 0) < 0.000001;
                      return (
                        <TableRow key={idx} hover>
                          <TableCell sx={{ fontWeight: 800 }}>
                            <Stack direction="row" spacing={1} alignItems="center">
                              <Box sx={{ fontSize: 18 }}>{flagFor(r.origin_country)}</Box>
                              <Box>
                                <Typography sx={{ fontWeight: 800, lineHeight: 1.1 }}>
                                  {r.origin_country}
                                </Typography>
                                <Typography variant="caption" sx={{ color: "#64748B" }}>
                                  {okZero ? "OK (en 0)" : "Pendiente por retirar"}
                                </Typography>
                              </Box>
                            </Stack>
                          </TableCell>

                          <TableCell>
                            <Chip label={r.fiat_currency} size="small" sx={{ fontWeight: 800 }} />
                          </TableCell>

                          <TableCell align="right" sx={{ color: "#16A34A", fontWeight: 800 }}>
                            {money(r.total_in || 0)}
                          </TableCell>

                          <TableCell align="right" sx={{ color: "#DC2626", fontWeight: 800 }}>
                            {money(r.total_out || 0)}
                          </TableCell>

                          <TableCell
                            align="right"
                            sx={{ fontWeight: 900, color: okZero ? "#16A34A" : "#2563EB" }}
                          >
                            {money(r.current_balance || 0)}
                          </TableCell>

                          <TableCell align="center">
                            <Stack direction="row" spacing={1} justifyContent="center">
                              <Button
                                size="small"
                                variant="outlined"
                                startIcon={<SendIcon />}
                                onClick={() => openWithdraw(r)}
                                disabled={r.current_balance <= 0}
                              >
                                Retirar
                              </Button>
                              <Button
                                size="small"
                                variant="contained"
                                startIcon={<EmptyIcon />}
                                onClick={() => openEmpty(r)}
                                disabled={r.current_balance <= 0}
                                sx={{ backgroundColor: "#4B2E83" }}
                              >
                                Vaciar
                              </Button>
                            </Stack>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 800 }}>
          {dialogMode === "withdraw" ? "Retirar monto" : "Vaciar billetera (dejar en 0)"}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Alert severity="info">
              Se registrará con fecha: <b>{todayISO()}</b>
            </Alert>

            <TextField label="País" value={selected?.origin_country || ""} disabled fullWidth />
            <TextField label="Moneda" value={selected?.fiat_currency || ""} disabled fullWidth />

            <Alert severity="info">
              Saldo actual: <b>{money(selected?.current_balance || 0)}</b>
            </Alert>

            {dialogMode === "withdraw" && (
              <TextField
                label="Monto a retirar"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                fullWidth
                required
                helperText="Ej: 500"
              />
            )}

            <TextField
              label="Nota (opcional)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              fullWidth
              multiline
              rows={2}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancelar</Button>
          <Button
            variant="contained"
            onClick={submitAction}
            disabled={actionLoading || !selected || (dialogMode === "withdraw" && !amount)}
            sx={{ backgroundColor: "#4B2E83" }}
          >
            {actionLoading ? "Procesando..." : dialogMode === "withdraw" ? "Retirar" : "Vaciar"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
