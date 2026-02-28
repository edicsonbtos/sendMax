'use client';

import React from 'react';
import { Card, Button, Typography, Avatar, LinearProgress, Chip } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import ListAltIcon from '@mui/icons-material/ListAlt';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import WorkspacePremiumIcon from '@mui/icons-material/WorkspacePremium';

export default function OperatorOfficePage() {
    // Mock Data
    const rates = [
        { currency: 'VEN (Bs)', rate: '45.12' },
        { currency: 'COL (COP)', rate: '3920.50' },
        { currency: 'PER (PEN)', rate: '3.75' }
    ];

    const grandPrix = [
        { rank: 1, name: 'Riccardo.O', score: 98, color: '#FFD700' },
        { rank: 2, name: 'Valeria.M', score: 85, color: '#C0C0C0' },
        { rank: 3, name: 'Carlos.T', score: 72, color: '#CD7F32' }
    ];

    const workQueue = [
        { id: 'ORD-991', client: 'Maria C.', amount: '$150.00', dest: 'Venezuela', status: 'Pending', beneficiary: 'Juan Perez - Banesco' },
        { id: 'ORD-992', client: 'Jose R.', amount: '$45.00', dest: 'Colombia', status: 'Pending', beneficiary: 'Carlos M - Bancolombia' }
    ];

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Header & Rates */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                    <Typography variant="h4" style={{ fontWeight: 800, color: '#0052FF' }}>Operator Terminal</Typography>
                    <Typography variant="subtitle1" color="textSecondary">Active Session • Sendmax 2.0</Typography>
                </div>
                <div style={{ display: 'flex', gap: '1rem', background: '#FFFFFF', padding: '0.75rem 1.5rem', borderRadius: '100px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}>
                    {rates.map(r => (
                        <div key={r.currency} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <TrendingUpIcon style={{ color: '#00BA88', fontSize: '1.2rem' }} />
                            <Typography variant="body2" style={{ fontWeight: 700 }}>{r.currency}: {r.rate}</Typography>
                        </div>
                    ))}
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '2rem' }}>

                {/* Left Column: Work Queue */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                    <Button
                        variant="contained"
                        fullWidth
                        size="large"
                        style={{
                            backgroundColor: '#0052FF',
                            color: 'white',
                            padding: '1rem',
                            borderRadius: '16px',
                            fontSize: '1.1rem',
                            display: 'flex',
                            gap: '0.5rem'
                        }}
                    >
                        <PlayArrowIcon />
                        Pre-load New Transfer
                    </Button>

                    <Card style={{ padding: '1.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
                            <ListAltIcon style={{ color: '#0052FF' }} />
                            <Typography variant="h6" style={{ fontWeight: 700 }}>My Work Queue</Typography>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            {workQueue.length === 0 ? (
                                <Typography color="textSecondary" align="center" style={{ padding: '2rem 0' }}>No pending orders assigned to you.</Typography>
                            ) : (
                                workQueue.map(order => (
                                    <div key={order.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', background: '#F9FAFB', borderRadius: '12px', border: '1px solid #F3F4F6' }}>
                                        <div>
                                            <Typography variant="subtitle2" style={{ fontWeight: 800, color: '#1A1A1A' }}>{order.id}</Typography>
                                            <Typography variant="body2" color="textSecondary">{order.client} • {order.dest}</Typography>
                                            <Typography variant="caption" color="textSecondary" style={{ display: 'block', marginTop: '4px' }}>Beneficiario: {order.beneficiary}</Typography>
                                        </div>
                                        <div style={{ textAlign: 'right' }}>
                                            <Typography variant="subtitle1" style={{ fontWeight: 700, color: '#00BA88' }}>{order.amount}</Typography>
                                            <Chip label={order.status} size="small" style={{ backgroundColor: '#FEF3C7', color: '#D97706', fontWeight: 600, fontSize: '0.7rem' }} />
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </Card>
                </div>

                {/* Right Column: Grand Prix */}
                <Card style={{ padding: '1.5rem', height: 'fit-content' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
                        <WorkspacePremiumIcon style={{ color: '#F4B740' }} />
                        <Typography variant="h6" style={{ fontWeight: 700 }}>Grand Prix (Top 3)</Typography>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        {grandPrix.map((op) => (
                            <div key={op.rank}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', alignItems: 'center' }}>
                                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                                        <Avatar style={{ background: op.color, width: 32, height: 32, fontWeight: 800, color: '#1A1A1A', fontSize: '0.9rem' }}>
                                            #{op.rank}
                                        </Avatar>
                                        <Typography variant="subtitle2" style={{ fontWeight: 700 }}>@{op.name}</Typography>
                                    </div>
                                    <Typography variant="subtitle2" style={{ fontWeight: 800, color: '#0052FF' }}>{op.score} pts</Typography>
                                </div>
                                <LinearProgress
                                    variant="determinate"
                                    value={op.score}
                                    sx={{
                                        height: 8,
                                        borderRadius: 4,
                                        backgroundColor: '#F3F4F6',
                                        '& .MuiLinearProgress-bar': { backgroundColor: op.color === '#FFD700' ? '#F4B740' : op.color }
                                    }}
                                />
                            </div>
                        ))}
                    </div>
                </Card>

            </div>
        </div>
    );
}
