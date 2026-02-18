"use client";

import React, { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  Button, Drawer, List, ListItem, ListItemButton, ListItemIcon,
  ListItemText, Box, Typography, Divider, Avatar, Stack, Chip,
  IconButton, useMediaQuery, useTheme,
} from "@mui/material";
import {
  Dashboard as DashboardIcon, Receipt as ReceiptIcon,
  AccountBalance as WalletIcon, EventNote as CalendarIcon,
  Settings as SettingsIcon, Assessment as MetricsIcon,
  Menu as MenuIcon, Close as CloseIcon, Logout as LogoutIcon,
  People as PeopleIcon,
} from "@mui/icons-material";
import { useAuth } from "@/components/AuthProvider";

const drawerWidth = 264;

const adminMenu = [
  { text: "Overview", path: "/", icon: <DashboardIcon />, description: "Dashboard principal" },
  { text: "Ordenes", path: "/orders", icon: <ReceiptIcon />, description: "Gestionar ordenes" },
  { text: "Billeteras Origen", path: "/origin", icon: <WalletIcon />, description: "Entradas y sweeps" },
  { text: "Metricas", path: "/metrics", icon: <MetricsIcon />, description: "Profit y volumen" },
  { text: "Cierre Diario", path: "/daily-close", icon: <CalendarIcon />, description: "Reportes y cierres" },
  { text: "Usuarios", path: "/users", icon: <PeopleIcon />, description: "Gestionar operadores" },
  { text: "Configuracion", path: "/settings", icon: <SettingsIcon />, description: "Reglas y margenes" },
    { text: "Metodos de Pago", path: "/payment-methods", icon: <WalletIcon />, description: "Metodos por pais" },
];

const operatorMenu = [
  { text: "Mi Dashboard", path: "/", icon: <DashboardIcon />, description: "Mis metricas" },
  { text: "Mis Ordenes", path: "/orders", icon: <ReceiptIcon />, description: "Mis operaciones" },
  { text: "Metricas", path: "/metrics", icon: <MetricsIcon />, description: "Mi rendimiento" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const [mobileOpen, setMobileOpen] = useState(false);
  const { logout, fullName, role, token } = useAuth();

  const menuItems = role === "admin" ? adminMenu : operatorMenu;

  const handleNav = (path: string) => {
    router.push(path);
    if (isMobile) setMobileOpen(false);
  };

  const getInitials = (name: string | null) => {
    if (!name) return "SM";
    return name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
  };

  const drawerContent = (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Box sx={{ p: 2.5, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Box onClick={() => handleNav("/")} sx={{ display: "flex", alignItems: "center", gap: 1.5, cursor: "pointer", transition: "opacity 0.2s ease", "&:hover": { opacity: 0.8 } }}>
          <Box component="img" src="/logo.png" alt="Sendmax" sx={{ height: 36, width: "auto", objectFit: "contain" }} />
          <Stack spacing={0}>
            <Typography variant="h6" sx={{ fontWeight: 700, color: "#4B2E83", fontSize: "1.1rem", lineHeight: 1.2, letterSpacing: "-0.01em" }}>Sendmax</Typography>
            <Typography variant="caption" sx={{ color: "#64748B", fontSize: "0.65rem", lineHeight: 1, letterSpacing: "0.05em", textTransform: "uppercase" }}>Backoffice</Typography>
          </Stack>
        </Box>
        {isMobile && (<IconButton onClick={() => setMobileOpen(false)} size="small"><CloseIcon /></IconButton>)}
      </Box>

      <Divider sx={{ borderColor: "#E9E3F7", mx: 2 }} />

      <List sx={{ px: 1.5, py: 2, flex: 1 }}>
        {menuItems.map((item) => {
          const isActive = item.path === "/" ? pathname === "/" : pathname.startsWith(item.path);
          return (
            <ListItem key={item.path} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton onClick={() => handleNav(item.path)} sx={{ borderRadius: "12px", py: 1.25, px: 1.5, backgroundColor: isActive ? "#EFEAFF" : "transparent", border: isActive ? "1px solid #D8CCFF" : "1px solid transparent", "&:hover": { backgroundColor: isActive ? "#EFEAFF" : "#FAF8FF", border: isActive ? "1px solid #D8CCFF" : "1px solid #E9E3F7" }, transition: "all 0.2s ease" }}>
                <ListItemIcon sx={{ color: isActive ? "#4B2E83" : "#6B7280", minWidth: 36, "& .MuiSvgIcon-root": { fontSize: 20 } }}>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} secondary={!isActive ? item.description : undefined} primaryTypographyProps={{ fontSize: "0.875rem", fontWeight: isActive ? 700 : 500, color: isActive ? "#4B2E83" : "#111827", lineHeight: 1.3 }} secondaryTypographyProps={{ fontSize: "0.65rem", color: "#64748B", lineHeight: 1.2, mt: 0.25 }} />
                {isActive && (<Box sx={{ width: 4, height: 24, borderRadius: 2, backgroundColor: "#4B2E83", ml: 1 }} />)}
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>

      <Divider sx={{ borderColor: "#E9E3F7", mx: 2 }} />

      <Box sx={{ p: 2, pb: 2.5 }}>
        {token && (<Button fullWidth variant="outlined" startIcon={<LogoutIcon />} onClick={logout} sx={{ mb: 1.5, borderColor: "#E9E3F7", color: "#64748B", fontSize: "0.8rem", "&:hover": { borderColor: "#DC2626", color: "#DC2626", backgroundColor: "#FDECEC" } }}>Cerrar Sesion</Button>)}
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Avatar sx={{ width: 32, height: 32, backgroundColor: "#EFEAFF", color: "#4B2E83", fontSize: "0.75rem", fontWeight: 700 }}>{getInitials(fullName)}</Avatar>
          <Stack spacing={0}>
            <Typography variant="caption" sx={{ color: "#111827", fontWeight: 600, fontSize: "0.75rem", lineHeight: 1.2 }}>{fullName || "Usuario"}</Typography>
            <Typography variant="caption" sx={{ color: "#64748B", fontSize: "0.65rem", lineHeight: 1.2 }}>{role === "admin" ? "Administrador" : "Operador"}</Typography>
          </Stack>
        </Stack>
        <Chip label="v1.3.0" size="small" sx={{ mt: 1.5, backgroundColor: "#EFEAFF", color: "#4B2E83", fontWeight: 600, fontSize: "0.65rem", height: 20 }} />
      </Box>
    </Box>
  );

  return (
    <>
      {isMobile && (<IconButton onClick={() => setMobileOpen(true)} sx={{ position: "fixed", top: 12, left: 12, zIndex: 1300, backgroundColor: "#FFFFFF", border: "1px solid #E9E3F7", boxShadow: "0 2px 8px rgba(17,24,39,.08)", "&:hover": { backgroundColor: "#FAF8FF" } }}><MenuIcon sx={{ color: "#4B2E83" }} /></IconButton>)}
      {isMobile ? (
        <Drawer variant="temporary" open={mobileOpen} onClose={() => setMobileOpen(false)} ModalProps={{ keepMounted: true }} sx={{ "& .MuiDrawer-paper": { width: drawerWidth, boxSizing: "border-box", background: "linear-gradient(180deg, #FFFFFF 0%, #FAF8FF 100%)", borderRight: "1px solid #E9E3F7" } }}>{drawerContent}</Drawer>
      ) : (
        <Drawer variant="permanent" sx={{ width: drawerWidth, flexShrink: 0, "& .MuiDrawer-paper": { width: drawerWidth, boxSizing: "border-box", background: "linear-gradient(180deg, #FFFFFF 0%, #FAF8FF 100%)", borderRight: "1px solid #E9E3F7", display: "flex", flexDirection: "column" } }}>{drawerContent}</Drawer>
      )}
    </>
  );
}
