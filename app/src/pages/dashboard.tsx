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
import type { Severity, Provenance, AlertStatus, Alert } from "@/services/types";
import { FindingDetails } from "@/components/dashboard/finding-details";
import { AnalysisSessions } from "@/components/dashboard/analysis-sessions";
import { DEFAULT_PAGE_SIZE } from "@/constants";
const Charts = lazy(() => import("@/components/dashboard/charts"));
export default function DashboardPage() {
  const { t } = useI18n();
  const [severity, setSeverity] = useState<Severity | "">("");
  const [offset, setOffset] = useState(0);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [provenance, setProvenance] = useState<Provenance>("analysis");
  const [historyVersion, setHistoryVersion] = useState(0);
  const [selectedFinding, setSelectedFinding] = useState<Alert | null>(null);
  const [busy, setBusy] = useState<Command | null>(null);
  const locked = useRef(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const resource = useDashboard(severity, offset, provenance, pageSize);
  const run = async (command: Command, id?: number, status: AlertStatus = "RESOLVED") => {
    if (locked.current) return;
    locked.current = true;
    setBusy(command);
    setNotice(null);
    try {
      if (command === "analyze") {
        const result = await api.fetchAndAnalyze();
        setNotice({
          key: result.analysis_session.file_issues.length ? "analysis_done_with_skips"
            : result.analysis_session.detector_status === "not_configured" ? "analysis_prepared" : "analysis_done",
          params: {
            conns: result.new_connections_ingested,
            alerts: result.new_alerts_detected,
            prepared: result.analysis_session.records_prepared,
            files: result.analysis_session.file_issues.length,
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
        setSelectedFinding(null);
      } else if (command === "resolve" && id !== undefined) {
        const updated = await api.updateAlertStatus(id, status);
        if (selectedFinding?.id === id) setSelectedFinding(updated);
        setNotice({ key: "alert_status_updated" });
      } else if (command === "csv" || command === "json") {
        await api.downloadAlertsExport(command, severity || undefined, provenance);
      }
    } catch (error) {
      setNotice({ key: errorKey(error), error: true });
    } finally {
      if (command !== "csv" && command !== "json") {
        if (command === "analyze" || command === "clear") setHistoryVersion(value => value + 1);
        await resource.refresh();
      }
      locked.current = false;
      setBusy(null);
    }
  };
  return (
    <div className="space-y-6 [overflow-anchor:none]">
      <Commands
        busy={busy}
        running={!!resource.data?.overview.running_session_id}
        run={(command) => {
          void run(command);
        }}
      />
      <OperationNotice notice={notice} close={() => setNotice(null)} />
      <DataState
        pageLoading
        loading={resource.loading && !resource.data}
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
            overview={resource.data.overview}
          />
          <AnalysisSessions refreshVersion={historyVersion} inspect={setSelectedFinding} />
          <Suspense fallback={<LoadingOrb text={t("loading")} />}>
            <Charts stats={resource.data.stats} protocols={resource.data.overview.protocols} />
          </Suspense>
          <Alerts
            loading={resource.loading}
            page={resource.data.alerts}
            severity={severity}
            onFilter={(value) => {
              setSeverity(value);
              setOffset(0);
            }}
            onPage={setOffset}
            onPageSize={(value) => { setPageSize(value); setOffset(0); }}
            busy={!!busy || resource.loading}
            provenance={provenance}
            onProvenance={(value) => { setProvenance(value); setOffset(0); setSelectedFinding(null); }}
            falsePositives={resource.data.stats.false_positive_count}
            inspect={setSelectedFinding}
            updateStatus={(id, status) => {
              void run("resolve", id, status);
            }}
          />
          {selectedFinding && <FindingDetails key={selectedFinding.id} alert={selectedFinding} close={() => setSelectedFinding(null)} />}
        </>
      )}
    </div>
  );
}
