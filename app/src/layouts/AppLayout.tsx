import { useCallback, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { Link, useNavigate } from "@/router";
import { ShieldAlert, Activity, LogOut, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SettingsDropdown } from "@/components/ui/settings-dropdown";
import { OperationNotice, type Notice } from "@/components/data-state";
import { useI18n } from "@/i18n";
import { useAuth } from "@/hooks/use-auth";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/services/api";
import { TIMING } from "@/constants";
export default function AppLayout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useI18n();
  const { user, logout } = useAuth();
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const loadHealth = useCallback(
    (signal: AbortSignal) => api.getHealth(signal),
    [],
  );
  const health = useResource(loadHealth, TIMING.DASHBOARD_POLL_INTERVAL);
  const handleLogout = async () => {
    setLoggingOut(true);
    setNotice(null);
    try {
      await logout();
      navigate("/login");
    } catch {
      setNotice({ key: "logout_error", error: true });
    } finally {
      setLoggingOut(false);
    }
  };
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b bg-card px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2">
          <Link to="/dashboard" className="flex items-center gap-2 font-bold">
            <ShieldAlert className="size-5 text-primary" />
            {t("hub_title")}
          </Link>
          <div className="flex items-center gap-1 sm:gap-3">
            <Badge variant="outline" className="hidden sm:inline-flex">
              {health.error
                ? t("sensor_offline")
                : health.data
                  ? t(
                      health.data.sensor_mode === "mock_mode"
                        ? "sensor_mock"
                        : "sensor_remote",
                    )
                  : t("loading")}
            </Badge>
            {user && (
              <span className="hidden text-xs text-muted-foreground sm:inline">
                {user.username}
              </span>
            )}
            <SettingsDropdown />
            <Button
              variant="ghost"
              size="icon"
              aria-label={t("logout")}
              disabled={loggingOut}
              onClick={() => {
                void handleLogout();
              }}
            >
              <LogOut className="size-4" />
            </Button>
          </div>
          <nav
            aria-label={t("navigation")}
            className="flex w-full items-center gap-1 pt-2"
          >
            <Button
              asChild
              variant={
                location.pathname === "/dashboard" ? "secondary" : "ghost"
              }
              size="sm"
            >
              <Link
                to="/dashboard"
                aria-current={
                  location.pathname === "/dashboard" ? "page" : undefined
                }
              >
                <Activity className="size-4" />
                {t("nav_dashboard")}
              </Link>
            </Button>
            <Button
              asChild
              variant={
                location.pathname === "/connections" ? "secondary" : "ghost"
              }
              size="sm"
            >
              <Link
                to="/connections"
                aria-current={
                  location.pathname === "/connections" ? "page" : undefined
                }
              >
                <Terminal className="size-4" />
                {t("nav_connections")}
              </Link>
            </Button>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl space-y-4 p-4 sm:p-6">
        <OperationNotice notice={notice} close={() => setNotice(null)} />
        {children}
      </main>
    </div>
  );
}
