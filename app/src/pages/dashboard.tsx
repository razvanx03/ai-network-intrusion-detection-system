import { useEffect, useState, useCallback } from "react";
import {
  ShieldAlert,
  AlertTriangle,
  Flame,
  CheckCircle2,
  RefreshCw,
  Trash2,
  Sparkles,
  Server,
  Check,
  AlertCircle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import { TIMING } from "@/constants";
import { cn } from "@/lib/utils";

export default function DashboardPage() {
  const { t } = useI18n();

  const [stats, setStats] = useState<any>({
    total_alerts: 0,
    critical_count: 0,
    high_count: 0,
    medium_count: 0,
    low_count: 0,
    unresolved_count: 0,
    top_attack_types: [],
    top_attacking_ips: [],
  });
  const [alerts, setAlerts] = useState<any[]>([]);
  const [connectionCount, setConnectionCount] = useState<number>(0);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>("");

  // Loading states
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isResettingSensor, setIsResettingSensor] = useState(false);
  const [isClearingDb, setIsClearingDb] = useState(false);
  const [bannerMessage, setBannerMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [alertStats, alertList, connHealth] = await Promise.all([
        api.getAlertStats(),
        api.getAlerts({ severity: severityFilter || undefined, limit: 25 }),
        api.getHealth(),
      ]);

      setStats(alertStats);
      setAlerts(alertList.items);
      setConnectionCount(connHealth.connections_total);
    } catch (err: any) {
      console.error("Failed to load dashboard data:", err);
    }
  }, [severityFilter]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, TIMING.DASHBOARD_POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [loadData]);

  // Action 1: Preia & Analizeaza
  const handleFetchAndAnalyze = async () => {
    setIsAnalyzing(true);
    setBannerMessage(null);
    try {
      const res = await api.fetchAndAnalyze();
      setBannerMessage(
        t("analysis_done", {
          conns: res.new_connections_ingested,
          alerts: res.new_alerts_detected,
        })
      );
      await loadData();
    } catch (err: any) {
      setBannerMessage(t("analysis_error", { error: err.message }));
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Action 2: Curata loguri de pe VM
  const handleResetSensor = async () => {
    setIsResettingSensor(true);
    setBannerMessage(null);
    try {
      const res = await api.resetSensor();
      setBannerMessage(t("sensor_reset_msg", { msg: res.message }));
    } catch (err: any) {
      setBannerMessage(t("sensor_reset_error", { error: err.message }));
    } finally {
      setIsResettingSensor(false);
    }
  };

  // Action 3: Curata baza de date locala
  const handleClearDatabase = async () => {
    if (!confirm(t("confirm_clear_db"))) return;
    setIsClearingDb(true);
    setBannerMessage(null);
    try {
      const res = await api.clearDatabase();
      setBannerMessage(res.message);
      await loadData();
    } catch (err: any) {
      setBannerMessage(t("clear_db_error", { error: err.message }));
    } finally {
      setIsClearingDb(false);
    }
  };

  // Status transition on alert
  const handleResolveAlert = async (id: number) => {
    try {
      await api.updateAlertStatus(id, "RESOLVED");
      await loadData();
    } catch (err) {
      console.error(err);
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case "CRITICAL":
        return <Badge variant="critical">CRITICAL</Badge>;
      case "HIGH":
        return <Badge variant="high">HIGH</Badge>;
      case "MEDIUM":
        return <Badge variant="medium">MEDIUM</Badge>;
      case "LOW":
        return <Badge variant="low">LOW</Badge>;
      default:
        return <Badge variant="secondary">{sev}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Control Bar */}
      <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl shadow-lg flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-400" />
            {t("console_title")}
          </h2>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Buton Preia si Analizeaza */}
          <Button
            onClick={handleFetchAndAnalyze}
            disabled={isAnalyzing || isResettingSensor || isClearingDb}
            className="bg-blue-600 hover:bg-blue-500 text-white gap-2 shadow-md min-w-[210px] justify-center cursor-pointer"
          >
            {isAnalyzing ? (
              <LoadingOrb state="solving" size={20} text={t("btn_analyzing")} />
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                <span>{t("btn_fetch_analyze")}</span>
              </>
            )}
          </Button>

          {/* Buton Curata loguri de pe VM */}
          <Button
            variant="outline"
            onClick={handleResetSensor}
            disabled={isAnalyzing || isResettingSensor || isClearingDb}
            className="gap-2 border-slate-700 hover:bg-slate-800 text-slate-200 min-w-[190px] justify-center cursor-pointer"
          >
            {isResettingSensor ? (
              <LoadingOrb state="connecting" size={20} text={t("btn_resetting_sensor")} />
            ) : (
              <>
                <Server className="w-4 h-4 text-amber-400" />
                <span>{t("btn_reset_sensor")}</span>
              </>
            )}
          </Button>

          {/* Buton Reset DB local */}
          <Button
            variant="ghost"
            onClick={handleClearDatabase}
            disabled={isAnalyzing || isResettingSensor || isClearingDb}
            className="text-slate-400 hover:text-red-400 gap-1.5 min-w-[100px] justify-center cursor-pointer"
            title={t("confirm_clear_db")}
          >
            {isClearingDb ? (
              <LoadingOrb state="working" size={20} text={t("btn_clearing_db")} color="#ef4444" />
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                <span>{t("btn_reset_db")}</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Banner Notificare */}
      {bannerMessage && (
        <div className="p-3 bg-blue-950/60 border border-blue-800/80 rounded-lg text-sm text-blue-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{bannerMessage}</span>
          </div>
          <button onClick={() => setBannerMessage(null)} className="text-blue-400 hover:text-white text-xs cursor-pointer">
            ✕
          </button>
        </div>
      )}

      {/* KPI Stats Cards - Compact */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <Card className="hover:border-slate-700/80 transition-all">
          <CardContent className="p-3.5 space-y-1">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>{t("stats_total_alerts")}</span>
              <ShieldAlert className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-2xl font-bold tracking-tight text-slate-100 leading-tight">
              {stats.total_alerts}
            </div>
            <div className="text-[11px] text-slate-400 flex items-center gap-1">
              <span className="font-semibold text-amber-400">{stats.unresolved_count}</span> {t("stats_unresolved")}
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-slate-700/80 transition-all">
          <CardContent className="p-3.5 space-y-1">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>{t("stats_critical")}</span>
              <Flame className="w-4 h-4 text-rose-500" />
            </div>
            <div className="text-2xl font-bold tracking-tight text-rose-400 leading-tight">
              {stats.critical_count}
            </div>
            <div className="text-[11px] text-slate-400">
              {t("stats_critical_sub")}
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-slate-700/80 transition-all">
          <CardContent className="p-3.5 space-y-1">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>{t("stats_high")}</span>
              <AlertTriangle className="w-4 h-4 text-orange-400" />
            </div>
            <div className="text-2xl font-bold tracking-tight text-orange-400 leading-tight">
              {stats.high_count}
            </div>
            <div className="text-[11px] text-slate-400">
              {t("stats_high_sub")}
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-slate-700/80 transition-all">
          <CardContent className="p-3.5 space-y-1">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>{t("stats_connections")}</span>
              <Server className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold tracking-tight text-emerald-400 leading-tight">
              {connectionCount}
            </div>
            <div className="text-[11px] text-slate-400">
              {t("stats_connections_sub")}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Alerts Table Card */}
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-blue-400" />
              {t("feed_title")}
            </CardTitle>
          </div>

          {/* Modern Cybersecurity Filter Pills Bar */}
          <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-950/70 border border-slate-800 rounded-xl shadow-inner">
            <button
              type="button"
              onClick={() => setSeverityFilter("")}
              className={cn(
                "px-2.5 py-1 text-xs rounded-lg transition-all duration-150 cursor-pointer select-none",
                severityFilter === ""
                  ? "bg-blue-600 text-white shadow-xs font-semibold"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              )}
            >
              {t("filter_all_severities")}
            </button>
            <button
              type="button"
              onClick={() => setSeverityFilter("CRITICAL")}
              className={cn(
                "px-2.5 py-1 text-xs rounded-lg transition-all duration-150 flex items-center gap-1.5 cursor-pointer select-none",
                severityFilter === "CRITICAL"
                  ? "bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-xs font-semibold"
                  : "text-slate-400 hover:text-rose-400 hover:bg-slate-800/60"
              )}
            >
              <span className={cn("w-1.5 h-1.5 rounded-full bg-rose-500", severityFilter === "CRITICAL" && "animate-pulse")} />
              CRITICAL
            </button>
            <button
              type="button"
              onClick={() => setSeverityFilter("HIGH")}
              className={cn(
                "px-2.5 py-1 text-xs rounded-lg transition-all duration-150 flex items-center gap-1.5 cursor-pointer select-none",
                severityFilter === "HIGH"
                  ? "bg-orange-500/20 text-orange-300 border border-orange-500/40 shadow-xs font-semibold"
                  : "text-slate-400 hover:text-orange-400 hover:bg-slate-800/60"
              )}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-orange-500" />
              HIGH
            </button>
            <button
              type="button"
              onClick={() => setSeverityFilter("MEDIUM")}
              className={cn(
                "px-2.5 py-1 text-xs rounded-lg transition-all duration-150 flex items-center gap-1.5 cursor-pointer select-none",
                severityFilter === "MEDIUM"
                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-xs font-semibold"
                  : "text-slate-400 hover:text-amber-400 hover:bg-slate-800/60"
              )}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
              MEDIUM
            </button>
            <button
              type="button"
              onClick={() => setSeverityFilter("LOW")}
              className={cn(
                "px-2.5 py-1 text-xs rounded-lg transition-all duration-150 flex items-center gap-1.5 cursor-pointer select-none",
                severityFilter === "LOW"
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-xs font-semibold"
                  : "text-slate-400 hover:text-emerald-400 hover:bg-slate-800/60"
              )}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              LOW
            </button>
          </div>
        </CardHeader>

        <CardContent>
          {alerts.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm">
              <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-500/50" />
              {t("no_alerts")}
              <p className="text-xs text-slate-600 mt-1">
                {t("no_alerts_hint")}
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[100px]">{t("th_severity")}</TableHead>
                  <TableHead>{t("th_attack_type")}</TableHead>
                  <TableHead>{t("th_source")}</TableHead>
                  <TableHead>{t("th_destination")}</TableHead>
                  <TableHead>{t("th_detector")}</TableHead>
                  <TableHead>{t("th_mitre")}</TableHead>
                  <TableHead>{t("th_status")}</TableHead>
                  <TableHead className="text-right">{t("th_action")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts.map((alert) => (
                  <TableRow key={alert.id}>
                    <TableCell>{getSeverityBadge(alert.severity)}</TableCell>
                    <TableCell className="font-semibold text-slate-100">
                      {alert.attack_type}
                      <p className="text-xs font-normal text-slate-400 line-clamp-1">{alert.description}</p>
                    </TableCell>
                    <TableCell>
                      <code className="text-xs font-mono text-blue-400">{alert.src_ip}</code>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-slate-300">{alert.dst_ip}</span>
                      {alert.dst_port && (
                        <span className="text-xs text-slate-500 font-mono ml-1">:{alert.dst_port}</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-slate-400">{alert.detector}</span>
                    </TableCell>
                    <TableCell>
                      {alert.mitre_technique ? (
                        <Badge variant="outline" className="text-[11px] font-mono border-slate-700 text-slate-300">
                          {alert.mitre_technique}
                        </Badge>
                      ) : (
                        <span className="text-xs text-slate-600">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={alert.status === "RESOLVED" ? "secondary" : "default"}
                        className="text-[11px]"
                      >
                        {alert.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {alert.status !== "RESOLVED" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleResolveAlert(alert.id)}
                          className="h-7 text-xs text-slate-400 hover:text-emerald-400 gap-1 cursor-pointer"
                        >
                          <Check className="w-3.5 h-3.5" />
                          {t("btn_resolve")}
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
