'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box, Typography, Card, Stack, Button, TextField,
  Alert, CircularProgress, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Chip, IconButton, Tooltip, InputAdornment,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  ToggleOn as ActiveIcon,
  ToggleOff as InactiveIcon,
  Visibility as ViewIcon,
  Search as SearchIcon,
  Close as ClearIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

/* ── tipos ─────────────────────────────────────────────── */

interface User {
  id: number;
  telegram_user_id: number;
  alias: string;
  full_name: string | null;
  email: string | null;
  role: string;
  is_active: boolean;
  kyc_status: string;
  balance_usdt: string | null;
  total_orders: number;
  created_at: string;
}

/* ── helpers ────────────────────────────────────────────── */

const KYC_MAP: Record<string, { color: 'success' | 'warning' | 'error' | 'default'; label: string }> = {
  APPROVED:  { color: 'success', label: 'Aprobado' },
  SUBMITTED: { color: 'warning', label: 'Enviado' },
  REJECTED:  { color: 'error',   label: 'Rechazado' },
  PENDING:   { color: 'default', label: 'Pendiente' },
};

function KycChip({ status }: { status: string }) {
  const cfg = KYC_MAP[status] ?? KYC_MAP.PENDING;
  return <Chip label={cfg.label} size="small" color={cfg.color} sx={{ fontWeight: 600, fontSize: 12 }} />;
}

function formatUsd(value: string | null | undefined): string {
  if (!value) return '$ 0.00';
  const num = parseFloat(value);
  if (isNaN(num)) return '$ 0.00';
  return `$ ${num.toFixed(2)}`;
}

/* ── componente principal ───────────────────────────────── */

export default function UsersPage() {
  const { token } = useAuth();
  const router = useRouter();
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState('');
  const [activeSearch, setActiveSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  /* ── fetch con búsqueda server-side ── */

  const fetchUsers = useCallback(async (q: string = '') => {
    setLoading(true);
    setError('');
    try {
      const query = q.trim() ? `?search=${encodeURIComponent(q.trim())}` : '';
      const res = await apiRequest<{ count: number; users: User[] }>(`/users${query}`);
      setUsers(res.users ?? []);
      setActiveSearch(q.trim());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error cargando usuarios');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) fetchUsers();
  }, [token, fetchUsers]);

  /* ── debounce 400ms al escribir ── */

  const handleSearchChange = useCallback((value: string) => {
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchUsers(value), 400);
  }, [fetchUsers]);

  const handleClearSearch = useCallback(() => {
    setSearch('');
    setActiveSearch('');
    if (debounceRef.current) clearTimeout(debounceRef.current);
    fetchUsers();
  }, [fetchUsers]);

  /* ── toggle activo/inactivo ── */

  const handleToggle = useCallback(async (userId: number) => {
    try {
      await apiRequest(`/users/${userId}/toggle`, { method: 'PUT' });
      await fetchUsers(activeSearch);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cambiar estado');
    }
  }, [activeSearch, fetchUsers]);

  /* ── render ── */

  return (
    <Box className="fade-in">

      {/* header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Usuarios</Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>
            {users.length} operadores y administradores
            {activeSearch && (
              <Chip
                label={`Filtro: "${activeSearch}"`}
                size="small"
                onDelete={handleClearSearch}
                sx={{ ml: 1, fontSize: 11 }}
              />
            )}
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={() => fetchUsers(activeSearch)}
          disabled={loading}
        >
          Actualizar
        </Button>
      </Stack>

      {/* búsqueda con debounce */}
      <TextField
        placeholder="Buscar por alias, nombre o email..."
        size="small"
        value={search}
        onChange={(e) => handleSearchChange(e.target.value)}
        sx={{ mb: 3, width: 420 }}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" sx={{ color: '#94A3B8' }} />
              </InputAdornment>
            ),
            endAdornment: search ? (
              <InputAdornment position="end">
                <IconButton size="small" onClick={handleClearSearch}>
                  <ClearIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ) : null,
          },
        }}
      />

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress sx={{ color: '#4B2E83' }} />
        </Box>
      ) : (
        <Card>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>ID</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Alias</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Nombre</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Telegram</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Rol</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>KYC</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="right">Balance</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="right">Ordenes</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Estado</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} align="center" sx={{ py: 6 }}>
                      <Typography variant="body2" color="text.secondary">
                        {activeSearch ? `Sin resultados para "${activeSearch}"` : 'Sin usuarios'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((u) => (
                    <TableRow
                      key={u.id}
                      hover
                      onClick={() => router.push(`/users/${u.id}`)}
                      sx={{ cursor: 'pointer' }}
                    >
                      <TableCell>{u.id}</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>{u.alias}</TableCell>
                      <TableCell>{u.full_name ?? '-'}</TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: 13 }}>
                        {u.telegram_user_id || '-'}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={u.role}
                          size="small"
                          color={u.role === 'admin' ? 'error' : 'primary'}
                          sx={{ fontWeight: 700, fontSize: 12 }}
                        />
                      </TableCell>
                      <TableCell><KycChip status={u.kyc_status} /></TableCell>
                      <TableCell align="right" sx={{ fontWeight: 600 }}>
                        {formatUsd(u.balance_usdt)}
                      </TableCell>
                      <TableCell align="right">{u.total_orders ?? 0}</TableCell>
                      <TableCell>
                        <Chip
                          icon={u.is_active ? <ActiveIcon /> : <InactiveIcon />}
                          label={u.is_active ? 'Activo' : 'Inactivo'}
                          size="small"
                          color={u.is_active ? 'success' : 'default'}
                        />
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <Stack direction="row" spacing={0.5}>
                          <Tooltip title="Ver detalle">
                            <IconButton size="small" onClick={() => router.push(`/users/${u.id}`)}>
                              <ViewIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title={u.is_active ? 'Desactivar' : 'Activar'}>
                            <IconButton size="small" onClick={() => handleToggle(u.id)}>
                              {u.is_active ? <InactiveIcon color="warning" /> : <ActiveIcon color="success" />}
                            </IconButton>
                          </Tooltip>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      )}
    </Box>
  );
}
