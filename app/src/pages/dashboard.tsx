import { errorKey } from "@/services/errors";
import { lazy, Suspense, useRef, useState } from "react";
import { Commands, type Command } from "@/components/dashboard/commands";
import { Metrics } from "@/components/dashboard/metrics";
import { Alerts } from "@/components/dashboard/alerts";
import {
  DataState,
  OperationNotice,
  type Notice,
} from "@/components/data-state";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { useDashboard } from "@/hooks/use-dashboard";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import type { Severity } from "@/services/types";
import { AnalysisSessions } from "@/components/dashboard/analysis-sessions";
const Charts = lazy(() => import("@/components/dashboard/charts"));
export default function DashboardPage() {
  const { t } = useI18n();
  const [severity, setSeverity] = useState<Severity | "">("");
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState<Command | null>(null);
  const locked = useRef(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const resource = useDashboard(severity, offset);
  const run = async (command: Command, id?: number) => {
    if (locked.current) return;
    locked.current = true;
    setBusy(command);
    setNotice(null);
    try {
      if (command === "analyze") {
        const result = await api.fetchAndAnalyze();
        setNotice({
          key: result.analysis_session.detector_status === "not_configured" ? "analysis_prepared" : "analysis_done",
          params: {
            conns: result.new_connections_ingested,
            alerts: result.new_alerts_detected,
            prepared: result.analysis_session.records_prepared,
          },
        });
      } else if (command === "sensor") {
        await api.resetSensor();
        setNotice({ key: "sensor_reset_done" });
      } else if (command === "clear") {
        const result = await api.clearDatabase();
        setNotice({
          key: "clear_db_done",
          params: {
            conns: result.deleted_connections,
            alerts: result.deleted_alerts,
          },
        });
        setOffset(0);
      } else if (command === "resolve" && id !== undefined) {
        await api.updateAlertStatus(id, "RESOLVED");
        setNotice({ key: "alert_resolved" });
      } else if (command === "csv" || command === "json") {
        await api.downloadAlertsExport(command, severity || undefined);
      }
      if (command === "clear" && offset !== 0) return;
      if (command !== "csv" && command !== "json") await resource.refresh();
    } catch (error) {
      setNotice({ key: errorKey(error), error: true });
    } finally {
      locked.current = false;
      setBusy(null);
    }
  };
  return (
    <div className="space-y-6">
      <Commands
        busy={busy}
        detectorStatus={resource.data?.health.detector_status}
        run={(command) => {
          void run(command);
        }}
      />
      <OperationNotice notice={notice} close={() => setNotice(null)} />
      <AnalysisSessions />
      <DataState
        loading={resource.loading}
        error={resource.error}
        hasData={!!resource.data}
        retry={() => {
          void resource.refresh();
        }}
      />
      {resource.data && (
        <>
          {resource.data.health.legacy_alerts_total > 0 && (
            <p className="text-sm text-muted-foreground">{t("legacy_demo_notice", { count: resource.data.health.legacy_alerts_total })}</p>
          )}
          <Metrics
            stats={resource.data.stats}
            connections={resource.data.health.connections_total}
          />
          <Suspense fallback={<LoadingOrb text={t("loading")} />}>
            <Charts stats={resource.data.stats} />
          </Suspense>
          <Alerts
            page={resource.data.alerts}
            severity={severity}
            onFilter={(value) => {
              setSeverity(value);
              setOffset(0);
            }}
            onPage={setOffset}
            busy={!!busy || resource.loading}
            resolve={(id) => {
              void run("resolve", id);
            }}
          />
        </>
      )}
    </div>
  );
}
