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
  { text: "Rutas Comision", path: "/routes", icon: <ReceiptIcon />, description: "Margenes por ruta" },
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
      {/* Logo Header */}
      <Box sx={{ p: 2.5, display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid rgba(0,229,255,0.1)" }}>
        <Box onClick={() => handleNav("/")} sx={{ display: "flex", alignItems: "center", gap: 1.5, cursor: "pointer", transition: "opacity 0.2s ease", "&:hover": { opacity: 0.8 } }}>
          <Box component="img" src="/logo.png" alt="Sendmax" sx={{ height: 36, width: "auto", objectFit: "contain" }} />
          <Stack spacing={0}>
            <Typography variant="h6" sx={{ fontWeight: 700, color: "#00E5FF", fontSize: "1.1rem", lineHeight: 1.2, letterSpacing: "-0.01em" }}>Sendmax</Typography>
            <Typography variant="caption" sx={{ color: "#7B2FBE", fontSize: "0.65rem", lineHeight: 1, letterSpacing: "0.05em", textTransform: "uppercase" }}>Backoffice</Typography>
          </Stack>
        </Box>
        {isMobile && (<IconButton onClick={() => setMobileOpen(false)} size="small" sx={{ color: "#00E5FF" }}><CloseIcon /></IconButton>)}
      </Box>

      {/* Navigation Menu */}
      <List sx={{ px: 1.5, py: 2, flex: 1 }}>
        {menuItems.map((item) => {
          const isActive = item.path === "/" ? pathname === "/" : pathname.startsWith(item.path);
          return (
            <ListItem key={item.path} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton 
                onClick={() => handleNav(item.path)} 
                sx={{ 
                  borderRadius: "12px", 
                  py: 1.25, 
                  px: 1.5, 
                  backgroundColor: isActive ? "rgba(0,229,255,0.08)" : "transparent", 
                  border: isActive ? "1px solid rgba(0,229,255,0.2)" : "1px solid transparent", 
                  "&:hover": { 
                    backgroundColor: isActive ? "rgba(0,229,255,0.12)" : "rgba(255,255,255,0.03)", 
                    border: "1px solid rgba(0,229,255,0.15)" 
                  }, 
                  transition: "all 0.2s ease" 
                }}>
                <ListItemIcon sx={{ color: isActive ? "#00E5FF" : "#888", minWidth: 36, "& .MuiSvgIcon-root": { fontSize: 20 } }}>{item.icon}</ListItemIcon>
                <ListItemText 
                  primary={item.text} 
                  secondary={!isActive ? item.description : undefined} 
                  primaryTypographyProps={{ 
                    fontSize: "0.875rem", 
                    fontWeight: isActive ? 700 : 500, 
                    color: isActive ? "#00E5FF" : "#e0e0e0", 
                    lineHeight: 1.3 
                  }} 
                  secondaryTypographyProps={{ 
                    fontSize: "0.65rem", 
                    color: "#555", 
                    lineHeight: 1.2, 
                    mt: 0.25 
                  }} 
                />
                {isActive && (<Box sx={{ width: 4, height: 24, borderRadius: 2, backgroundColor: "#00E5FF", ml: 1, boxShadow: "0 0 8px rgba(0,229,255,0.5)" }} />)}
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>

      <Divider sx={{ borderColor: "rgba(0,229,255,0.1)", mx: 2 }} />

      {/* User Profile Footer */}
      <Box sx={{ p: 2, pb: 2.5 }}>
        {token && (
          <Button 
            fullWidth 
            variant="outlined" 
            startIcon={<LogoutIcon />} 
            onClick={logout} 
            sx={{ 
              mb: 1.5, 
              borderColor: "rgba(255,107,107,0.3)", 
              color: "#ff6b6b", 
              fontSize: "0.8rem", 
              "&:hover": { 
                borderColor: "#ff6b6b", 
                backgroundColor: "rgba(255,107,107,0.08)" 
              } 
            }}
          >
            Cerrar Sesion
          </Button>
        )}
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Avatar sx={{ 
            width: 32, 
            height: 32, 
            backgroundColor: "rgba(0,229,255,0.15)", 
            color: "#00E5FF", 
            fontSize: "0.75rem", 
            fontWeight: 700,
            border: "1px solid rgba(0,229,255,0.3)"
          }}>
            {getInitials(fullName)}
          </Avatar>
          <Stack spacing={0}>
            <Typography variant="caption" sx={{ color: "#e0e0e0", fontWeight: 600, fontSize: "0.75rem", lineHeight: 1.2 }}>{fullName || "Usuario"}</Typography>
            <Typography variant="caption" sx={{ color: "#7B2FBE", fontSize: "0.65rem", lineHeight: 1.2 }}>{role === "admin" ? "Administrador" : "Operador"}</Typography>
          </Stack>
        </Stack>
        <Chip 
          label="v1.3.0" 
          size="small" 
          sx={{ 
            mt: 1.5, 
            backgroundColor: "rgba(123,47,190,0.15)", 
            color: "#7B2FBE", 
            fontWeight: 600, 
            fontSize: "0.65rem", 
            height: 20,
            border: "1px solid rgba(123,47,190,0.3)"
          }} 
        />
      </Box>
    </Box>
  );

  return (
    <>
      {isMobile && (
        <IconButton 
          onClick={() => setMobileOpen(true)} 
          sx={{ 
            position: "fixed", 
            top: 12, 
            left: 12, 
            zIndex: 1300, 
            backgroundColor: "#0a0a0a", 
            border: "1px solid rgba(0,229,255,0.2)", 
            boxShadow: "0 4px 16px rgba(0,0,0,0.5)", 
            "&:hover": { 
              backgroundColor: "#111", 
              borderColor: "#00E5FF" 
            } 
          }}
        >
          <MenuIcon sx={{ color: "#00E5FF" }} />
        </IconButton>
      )}
      {isMobile ? (
        <Drawer 
          variant="temporary" 
          open={mobileOpen} 
          onClose={() => setMobileOpen(false)} 
          ModalProps={{ keepMounted: true }} 
          sx={{ 
            "& .MuiDrawer-paper": { 
              width: drawerWidth, 
              boxSizing: "border-box", 
              background: "linear-gradient(180deg, #0a0a0a 0%, #050505 100%)", 
              borderRight: "1px solid rgba(0,229,255,0.1)" 
            } 
          }}
        >
          {drawerContent}
        </Drawer>
      ) : (
        <Drawer 
          variant="permanent" 
          sx={{ 
            width: drawerWidth, 
            flexShrink: 0, 
            "& .MuiDrawer-paper": { 
              width: drawerWidth, 
              boxSizing: "border-box", 
              background: "linear-gradient(180deg, #0a0a0a 0%, #050505 100%)", 
              borderRight: "1px solid rgba(0,229,255,0.1)", 
              display: "flex", 
              flexDirection: "column" 
            } 
          }}
        >
          {drawerContent}
        </Drawer>
      )}
    </>
  );
}
