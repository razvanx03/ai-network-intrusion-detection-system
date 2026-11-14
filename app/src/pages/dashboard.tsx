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
import { clearResourceCache } from "@/hooks/use-resource";
import { useUrlPagination } from "@/hooks/use-url-pagination";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import type { AlertStatus, Alert } from "@/services/types";
import { FindingDetails } from "@/components/dashboard/finding-details";
import { AnalysisSessions } from "@/components/dashboard/analysis-sessions";

import { useSensorSync } from "@/hooks/use-sensor-sync";
const Charts = lazy(() => import("@/components/dashboard/charts"));
export default function DashboardPage() {
  const sync = useSensorSync();
  const { t } = useI18n();
  const {
    limit: pageSize,
    offset,
    setOffset,
    setLimit: setPageSize,
  } = useUrlPagination({
    pageParam: "page",
    limitParam: "limit",
  });

  const [historyVersion, setHistoryVersion] = useState(0);
  const [selectedAlertIds, setSelectedAlertIds] = useState<number[]>([]);
  const [protocols, setProtocols] = useState<string[]>([]);
  const [selectedFinding, setSelectedFinding] = useState<Alert | null>(null);
  const [busy, setBusy] = useState<Command | null>(null);
  const locked = useRef(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const resource = useDashboard(offset, pageSize, protocols);
  const run = async (command: Command, id?: number | number[], status: AlertStatus = "RESOLVED") => {
    if (locked.current) return;
    locked.current = true;
    setBusy(command);
    setNotice(null);
    try {
      if (command === "analyze") {
        const result = await sync.analyze();
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
      } else if (command === "archive") {
        await api.archiveDatabase();
        clearResourceCache();
        setNotice({ key: "archive_done" });
        setOffset(0);
        setSelectedFinding(null);
        setSelectedAlertIds([]);
      } else if (command === "resolve" && id !== undefined) {
        if (Array.isArray(id)) {
          const result = await api.updateAlertStatuses(id, status);
          if (selectedFinding && id.includes(selectedFinding.id)) setSelectedFinding({ ...selectedFinding, status });
          setSelectedAlertIds([]);
          setNotice({ key: "alerts_status_updated", params: { count: result.updated } });
        } else {
          const updated = await api.updateAlertStatus(id, status);
          if (selectedFinding?.id === id) setSelectedFinding(updated);
          setNotice({ key: "alert_status_updated" });
        }
      } else if (command === "csv" || command === "json") {
        await api.downloadAlertsExport(command);
      }
    } catch (error) {
      setNotice({ key: errorKey(error), error: true });
    } finally {
      try {
        if (command !== "csv" && command !== "json" && command !== "analyze") {
          if (command === "archive") setHistoryVersion(value => value + 1);
          await resource.refresh();
        }
      } finally {
        locked.current = false;
        setBusy(null);
      }
    }
  };
  return (
    <div className="space-y-6 [overflow-anchor:none]">
      <Commands
        busy={busy}
        running={sync.syncing || !!resource.data?.overview.running_session_id}
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
          <Metrics
            stats={resource.data.stats}
            overview={resource.data.overview}
          />
          <AnalysisSessions refreshVersion={historyVersion} inspect={setSelectedFinding} />
          <Suspense fallback={<LoadingOrb text={t("loading")} />}>
            <Charts protocols={resource.data.overview.protocols} />
          </Suspense>
          <Alerts
            protocols={protocols}
            onProtocolsChange={values => { setProtocols(values); setOffset(0); setSelectedAlertIds([]); }}
            loading={resource.alertsLoading}
            page={resource.data.alerts}
            onPage={value => { setSelectedAlertIds([]); setOffset(value); }}
            onPageSize={value => { setSelectedAlertIds([]); setPageSize(value); }}
            selectedIds={selectedAlertIds}
            onSelectionChange={setSelectedAlertIds}
            updateSelectedStatus={status => { void run("resolve", selectedAlertIds, status); }}
            busy={!!busy || resource.loading}
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
