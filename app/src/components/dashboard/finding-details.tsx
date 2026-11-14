import { useCallback } from "react";
import { Modal } from "@/components/modal";
import { PacketsHeading } from "@/components/packets-heading";
import { ConnectionContext } from "@/components/connection-context";
import { AlertStatusBadge } from "@/components/alert-status-badge";
import { Table, TableHead, TableHeader, TableRow, TableBody, TableCell } from "@/components/ui/table";
import { DataState } from "@/components/data-state";
import { LoadingRegion } from "@/components/loading-region";
import { useResource } from "@/hooks/use-resource";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import type { Alert, Connection } from "@/services/types";

export function FindingDetails({ alert, close, includeArchived = false }: { alert: Alert; close: () => void; includeArchived?: boolean }) {
  const { t, language } = useI18n();
  const load = useCallback(async (signal: AbortSignal): Promise<Connection[]> => {
    if (!alert.analysis_session_id) return [];
    return api.getAlertConnections(alert.analysis_session_id, alert.id, signal, includeArchived);
  }, [alert.id, alert.analysis_session_id, includeArchived]);
  const resource = useResource(load);
  return <Modal open onOpenChange={open => { if (!open) close(); }} title={t("finding_inspect", { id: alert.id })}>
    <div className="space-y-4">
      <dl className="grid gap-3 text-sm sm:grid-cols-3">
        <div><dt className="text-muted-foreground">{t("finding_time")}</dt><dd>{new Date(alert.timestamp).toLocaleString(language === "ro" ? "ro-RO" : "en-GB")}</dd></div>
        <div><dt className="text-muted-foreground">{t("model_score")}</dt><dd className="tabular-nums">{alert.confidence.toFixed(3)}</dd></div>
        <div><dt className="text-muted-foreground">{t("th_status")}</dt><dd className="mt-1"><AlertStatusBadge status={alert.status} /></dd></div>
      </dl>
      {alert.mitre_technique && <p className="text-sm">{t("th_mitre")}: {alert.mitre_technique}</p>}
      <h3 className="text-sm font-medium">{t("finding_evidence")}</h3>
      {!alert.analysis_session_id ? <p className="text-sm text-muted-foreground">{t("finding_legacy_evidence")}</p> : <>
        <DataState loading={false} error={resource.error} hasData={!!resource.data} retry={() => { void resource.refresh(); }} />
        <LoadingRegion loading={resource.loading}>
        {resource.data && (resource.data.length ? <Table>
          <TableHeader><TableRow><TableHead>{t("th_uid")}</TableHead><TableHead>{t("th_source")}</TableHead><TableHead>{t("th_destination")}</TableHead><TableHead>{t("th_protocol")}</TableHead><TableHead>{t("th_duration")}</TableHead><TableHead>{t("th_bytes")}</TableHead><TableHead><PacketsHeading /></TableHead><TableHead>{t("th_conn_state")}</TableHead></TableRow></TableHeader>
          <TableBody>{resource.data.map(connection => <TableRow key={connection.id}>
            <TableCell className="font-mono text-xs">{connection.uid}</TableCell>
            <TableCell className="font-mono text-xs">{connection.src_ip}:{connection.src_port}</TableCell>
            <TableCell className="font-mono text-xs">{connection.dst_ip}:{connection.dst_port}</TableCell>
            <TableCell>{connection.proto.toUpperCase()}</TableCell>
            <TableCell>{connection.duration?.toFixed(3) ?? "—"}</TableCell>
            <TableCell>{connection.orig_bytes ?? "—"} / {connection.resp_bytes ?? "—"}</TableCell>
            <TableCell>{connection.orig_pkts ?? "—"} / {connection.resp_pkts ?? "—"}</TableCell>
            <TableCell>{connection.conn_state ?? "—"}</TableCell>
          </TableRow>)}</TableBody>
        </Table> : <p className="text-sm text-muted-foreground">{t("analysis_no_records")}</p>)}
        </LoadingRegion>
        {resource.data?.filter(connection => connection.available_logs.some(kind => kind !== "conn")).map(connection =>
          <ConnectionContext key={connection.id} connection={connection} includeArchived={includeArchived} showSummary={(resource.data?.length ?? 0) > 1} />)}
      </>}
    </div>
  </Modal>;
}
