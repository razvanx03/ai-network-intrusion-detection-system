import { useEffect, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { Link, useNavigate } from "@/router";
import { Archive, ShieldAlert, Activity, LogOut, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SettingsDropdown } from "@/components/ui/settings-dropdown";
import { OperationNotice, type Notice } from "@/components/data-state";
import { useI18n } from "@/i18n";
import { useAuth } from "@/hooks/use-auth";
import { UbuntuStatus } from "@/components/ubuntu-status";
import { SensorSyncProvider } from "@/contexts/SensorSyncProvider";
import { useSensorSync } from "@/hooks/use-sensor-sync";
import { errorKey } from "@/services/errors";
export default function AppLayout({ children }: { children: ReactNode }) {
  return <SensorSyncProvider><LayoutContent>{children}</LayoutContent></SensorSyncProvider>;
}
function LayoutContent({ children }: { children: ReactNode }) {
  const sync = useSensorSync();
  const navigate = useNavigate();
  const location = useLocation();
  const contentWidth = "max-w-[1600px]";
  const { t } = useI18n();
  const { user, logout } = useAuth();
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [location.pathname]);
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
      <header className="sticky top-0 z-30 border-b bg-card">
        <div className={`mx-auto w-full ${contentWidth} px-4 sm:px-6`}>
          <div className="flex min-h-14 flex-wrap items-center justify-between gap-x-4 gap-y-2 py-2 sm:h-14 sm:flex-nowrap sm:py-0">
          <Link to="/dashboard" className="flex items-center gap-2 font-bold shrink-0">
            <ShieldAlert className="size-5 text-primary" />
            {t("hub_title")}
          </Link>
          <div className="flex items-center justify-end gap-1 sm:gap-3 shrink-0">
            <UbuntuStatus />
            {user && (
              <span className="hidden text-xs text-muted-foreground sm:inline">
                {user.username}
              </span>
            )}
            <SettingsDropdown />
            <Button
              variant="ghost"
              size="icon"
              className="size-8 sm:size-10"
              aria-label={t("logout")}
              disabled={loggingOut}
              onClick={() => {
                void handleLogout();
              }}
            >
              <LogOut className="size-4" />
            </Button>
          </div>
          </div>
          <nav
            aria-label={t("navigation")}
            className="flex h-11 items-center gap-1 border-t border-border/40 pb-1 overflow-x-auto"
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
            <Button asChild variant={location.pathname === "/all-data" || location.pathname.startsWith("/archive-batches/") ? "secondary" : "ghost"} size="sm">
              <Link to="/all-data" aria-current={location.pathname === "/all-data" ? "page" : undefined}>
                <Archive className="size-4" />{t("archive_nav")}
              </Link>
            </Button>
          </nav>
        </div>
      </header>
      <main className={`mx-auto w-full ${contentWidth} min-h-[calc(100vh-6.25rem)] space-y-4 p-4 sm:p-6`}>
        <OperationNotice notice={sync.error ? { key: errorKey(sync.error), error: true } : null} close={sync.dismissError} />
        <OperationNotice notice={notice} close={() => setNotice(null)} />
        {children}
      </main>
    </div>
  );
}
