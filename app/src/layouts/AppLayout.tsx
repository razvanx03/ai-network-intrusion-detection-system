import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Link, useNavigate } from "@/router";
import { ShieldAlert, Activity, Wifi, LogOut, Terminal, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SettingsDropdown } from "@/components/ui/settings-dropdown";
import { useI18n } from "@/i18n";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/services/api";

interface AppLayoutProps {
  children: React.ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useI18n();
  const { user, logout } = useAuth();
  const [sensorStatus, setSensorStatus] = useState<string>("...");

  useEffect(() => {
    let isMounted = true;
    api
      .getHealth()
      .then((h) => {
        if (!isMounted) return;
        if (h.sensor_mode === "mock_mode") {
          setSensorStatus(t("sensor_mock"));
        } else {
          setSensorStatus(t("sensor_remote"));
        }
      })
      .catch(() => {
        if (isMounted) setSensorStatus(t("sensor_offline"));
      });

    return () => {
      isMounted = false;
    };
  }, [location.pathname, t]);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans transition-colors duration-150">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <Link to="/dashboard" className="flex items-center space-x-3 text-blue-400 hover:text-blue-300 transition-colors">
            <div className="p-2 bg-blue-950/80 border border-blue-800/60 rounded-lg">
              <ShieldAlert className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <span className="font-bold text-slate-100 text-base tracking-wide">
                {t("hub_title")}
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center space-x-1 pl-4 border-l border-slate-800">
            <Link to="/dashboard">
              <Button
                variant={location.pathname === "/dashboard" ? "secondary" : "ghost"}
                size="sm"
                className="gap-2"
              >
                <Activity className="w-4 h-4" />
                {t("nav_dashboard")}
              </Button>
            </Link>
            <Link to="/connections">
              <Button
                variant={location.pathname === "/connections" ? "secondary" : "ghost"}
                size="sm"
                className="gap-2"
              >
                <Terminal className="w-4 h-4" />
                {t("nav_connections")}
              </Button>
            </Link>
          </nav>
        </div>

        {/* Right Info, Settings & Actions */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-950/70 border border-slate-800 px-3 py-1.5 rounded-md text-xs">
            <Wifi className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span className="text-slate-400">{t("sensor_label")}:</span>
            <span className="text-slate-200 font-medium">{sensorStatus}</span>
          </div>

          {/* Settings Dropdown (Language & Theme) */}
          <SettingsDropdown />

          {user && (
            <>
              <div className="h-5 w-px bg-slate-800" />
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="hidden sm:inline-flex gap-1.5 py-1">
                  <Lock className="w-3 h-3 text-blue-400" />
                  {user.username}
                </Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleLogout}
                  className="text-slate-400 hover:text-red-400"
                  title={t("logout")}
                >
                  <LogOut className="w-4 h-4" />
                </Button>
              </div>
            </>
          )}
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
        {children}
      </main>
    </div>
  );
}
