'use client';

import React, { useState, useEffect } from 'react';
import { 
  Box, Typography, Card, Table, TableBody, TableCell, TableHead, TableRow, 
  Alert, CircularProgress, Chip, IconButton, Tooltip, Dialog, DialogTitle, 
  DialogContent, Button, DialogActions 
} from '@mui/material';
import { Info as InfoIcon } from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

interface AuditItem {
    id: number;
    actor_user_id: number | null;
    action: string;
    entity_type: string;
    entity_id: string;
    before_json: any;
    after_json: any;
    created_at: string;
    ip: string;
    user_agent: string;
}

export default function AuditLogPage() {
    const { token, role } = useAuth();
    const [items, setItems] = useState<AuditItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [selected, setSelected] = useState<AuditItem | null>(null);

    useEffect(() => {
        if (token && role === 'admin') {
            fetchData();
        }
    }, [token, role]);

    const fetchData = async () => {
        setLoading(true);
        setError('');
        try {
            const data = await apiRequest<{items: AuditItem[]}>('/admin/audit-log');
            setItems(data.items);
        } catch (err: any) {
            setError(err.message || 'Error fetching audit log');
        } finally {
            setLoading(false);
        }
    };

    if (role !== 'admin') {
        return <Alert severity="error">Acceso restringido a administradores.</Alert>;
    }

    return (
        <Box className="fade-in">
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#111827', mb: 1 }}>Audit Log</Typography>
            <Typography variant="body2" sx={{ color: '#64748B', mb: 4 }}>Historial de cambios de configuración y acciones administrativas ejecutadas en el sistema.</Typography>

            {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

            <Card sx={{ borderRadius: '16px', overflow: 'auto', border: '1px solid #E9E3F7', mb: 4 }}>
                <Table size="small" sx={{ minWidth: 800 }}>
                    <TableHead sx={{ backgroundColor: '#F8FAFC' }}>
                        <TableRow>
                            <TableCell sx={{ fontWeight: 600 }}>ID</TableCell>
                            <TableCell sx={{ fontWeight: 600 }}>Fecha</TableCell>
                            <TableCell sx={{ fontWeight: 600 }}>Actor</TableCell>
                            <TableCell sx={{ fontWeight: 600 }}>Acción</TableCell>
                            <TableCell sx={{ fontWeight: 600 }}>Entidad</TableCell>
                            <TableCell align="center" sx={{ fontWeight: 600 }}>Compara</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {loading ? (
                            <TableRow><TableCell colSpan={6} align="center" sx={{ py: 8 }}><CircularProgress /></TableCell></TableRow>
                        ) : items.length === 0 ? (
                            <TableRow><TableCell colSpan={6} align="center" sx={{ py: 8 }}>No hay registros de auditoría</TableCell></TableRow>
                        ) : items.map((row) => (
                            <TableRow key={row.id} hover>
                                <TableCell>{row.id}</TableCell>
                                <TableCell>{new Date(row.created_at).toLocaleString('es-VE')}</TableCell>
                                <TableCell>{row.actor_user_id ? `UID: ${row.actor_user_id}` : 'Sistema / API'}</TableCell>
                                <TableCell>
                                    <Chip 
                                        size="small" 
                                        label={row.action} 
                                        sx={{ 
                                            fontWeight: 700, 
                                            backgroundColor: '#EFEAFF', 
                                            color: '#4B2E83',
                                            borderRadius: '6px'
                                        }} 
                                    />
                                </TableCell>
                                <TableCell>{row.entity_type} <Typography component="span" variant="caption" sx={{ color: '#64748B' }}>({row.entity_id})</Typography></TableCell>
                                <TableCell align="center">
                                    <Tooltip title="Ver detalle JSON">
                                        <IconButton size="small" onClick={() => setSelected(row)} sx={{ backgroundColor: '#F1F5F9' }}>
                                            <InfoIcon fontSize="small" sx={{ color: '#3B82F6' }} />
                                        </IconButton>
                                    </Tooltip>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </Card>

            <Dialog open={!!selected} onClose={() => setSelected(null)} maxWidth="md" fullWidth>
                <DialogTitle sx={{ fontWeight: 800 }}>
                    Detalle Audit #{selected?.id} 
                    <Typography component="span" variant="body2" sx={{ ml: 2, color: '#64748B' }}>
                        Acción: {selected?.action}
                    </Typography>
                </DialogTitle>
                <DialogContent dividers>
                    <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                            <Typography variant="subtitle2" sx={{ mb: 1, color: '#DC2626', fontWeight: 700 }}>Valor Anterior (Before)</Typography>
                            <Box component="pre" sx={{ p: 2, backgroundColor: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '8px', overflow: 'auto', fontSize: '0.8rem', maxHeight: 400 }}>
                                {selected?.before_json ? JSON.stringify(selected.before_json, null, 2) : 'null'}
                            </Box>
                        </Box>
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                            <Typography variant="subtitle2" sx={{ mb: 1, color: '#16A34A', fontWeight: 700 }}>Valor Nuevo (After)</Typography>
                            <Box component="pre" sx={{ p: 2, backgroundColor: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '8px', overflow: 'auto', fontSize: '0.8rem', maxHeight: 400 }}>
                                {selected?.after_json ? JSON.stringify(selected.after_json, null, 2) : 'null'}
                            </Box>
                        </Box>
                    </Box>
                </DialogContent>
                <DialogActions sx={{ p: 2 }}>
                    <Button onClick={() => setSelected(null)} variant="contained" sx={{ backgroundColor: '#111827' }} disableElevation>Cerrar</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
