import { useCallback, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { Pagination } from "@/components/pagination";
import { DataState } from "@/components/data-state";
import { useResource } from "@/hooks/use-resource";
import { useI18n, type TranslationKey } from "@/i18n";
import { api } from "@/services/api";
import { attackKeys } from "@/lib/display";
import type { Alert } from "@/services/types";

const errorLabels: Record<string, TranslationKey> = {
  invalid_records: "analysis_error_records",
  sensor_unavailable: "analysis_error_sensor",
  cursor_conflict: "analysis_error_conflict",
  detector_failed: "analysis_error_detector",
  processing_failed: "analysis_error_processing",
  server_restarted: "analysis_error_restart",
  request_interrupted: "analysis_error_interrupted",
};

export function AnalysisSessions({ inspect }: { inspect: (alert: Alert) => void }) {
  const { t, language } = useI18n();
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [recordOffset, setRecordOffset] = useState(0);
  const [alertOffset, setAlertOffset] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const load = useCallback(async (signal: AbortSignal) => {
    const history = await api.getAnalysisSessions(offset, signal);
    const session = selected && history.total > 0
      ? await api.getAnalysisSession(selected, signal)
      : history.items[0] ?? null;
    const details = session && expanded ? await Promise.all([
      api.getAnalysisConnections(session.id, recordOffset, signal),
      api.getAnalysisAlerts(session.id, alertOffset, signal),
    ]) : null;
    return { history, session, details };
  }, [offset, selected, recordOffset, alertOffset, expanded]);
  // Poll status only. Analysis itself always requires an explicit user command.
  const resource = useResource(load, 3000);
  const data = resource.data;
  return (
    <Card>
      <CardHeader><CardTitle>{t("analysis_sessions")}</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <DataState loading={resource.loading && !data} error={resource.error} hasData={!!data} retry={() => { void resource.refresh(); }} />
        {data && !data.history.items.length && <p className="text-sm text-muted-foreground">{t("analysis_no_sessions")}</p>}
        {data && data.history.items.length > 0 && <>
          <div className="flex flex-wrap gap-2" role="group" aria-label={t("analysis_sessions")}>
            {data.history.items.map((session) => <Button
              key={session.id} variant={session.id === data.session?.id ? "secondary" : "outline"}
              size="sm" aria-pressed={session.id === data.session?.id}
              aria-label={t("analysis_select", { id: session.id })}
              onClick={() => { setSelected(session.id); setRecordOffset(0); setAlertOffset(0); setExpanded(true); }}
            >
              <span className="font-mono">{session.id.slice(0, 8)}</span>
              {t(`analysis_status_${session.status}`)}
            </Button>)}
          </div>
          <Pagination offset={data.history.offset} limit={data.history.limit} total={data.history.total}
            loading={resource.loading} onChange={(value) => { setOffset(value); setSelected(null); setRecordOffset(0); setAlertOffset(0); }} />
        </>}
        {data?.session && <div className="space-y-3 border-t pt-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{t(`analysis_status_${data.session.status}`)}</Badge>
            <Badge variant="outline">{t(`analysis_source_${data.session.source}`)}</Badge>
            <span className="text-xs text-muted-foreground">{new Date(data.session.started_at).toLocaleString(language === "ro" ? "ro-RO" : "en-GB")}</span>
            {data.session.detector_status === "configured" && <Badge variant="outline">{data.session.detector_name.startsWith("random_forest") ? t("model_random_forest") : data.session.detector_name}</Badge>}
            {data.session.status === "running" && <LoadingOrb size={20} text={t("btn_analyzing")} />}
          </div>
          <p className="text-sm" aria-live="polite">{t("analysis_counts", {
            imported: data.session.new_connections_ingested,
            prepared: data.session.records_prepared,
            alerts: data.session.new_alerts_detected,
          })}</p>
          {data.session.finished_at && <p className="text-xs text-muted-foreground">{t("analysis_finished", { time: new Date(data.session.finished_at).toLocaleString(language === "ro" ? "ro-RO" : "en-GB"), seconds: Math.max(0, (new Date(data.session.finished_at).getTime() - new Date(data.session.started_at).getTime()) / 1000).toFixed(1) })}</p>}
          {data.session.detector_status === "not_configured" && <p className="text-sm text-muted-foreground">{t("analysis_no_detector")}</p>}
          {data.session.error_code && <p role="alert" className="text-sm text-destructive">{t(errorLabels[data.session.error_code] ?? "analysis_error_processing")}</p>}
          <Button variant="outline" size="sm" aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>{t(expanded ? "analysis_hide_details" : "analysis_show_details")}</Button>
          {expanded && data.details && <>
          <h3 className="text-sm font-medium">{t("analysis_records")}</h3>
          {data.details[0].items.length ? <Table>
            <TableHeader><TableRow>
              <TableHead>{t("th_uid")}</TableHead><TableHead>{t("analysis_origin")}</TableHead>
              <TableHead>{t("th_destination")}</TableHead><TableHead>{t("th_protocol")}</TableHead>
            </TableRow></TableHeader>
            <TableBody>{data.details[0].items.map(({ connection, file }) => <TableRow key={connection.id}>
              <TableCell className="font-mono text-xs" title={file ?? undefined}>{connection.uid}</TableCell>
              <TableCell className="font-mono text-xs">{connection.src_ip}:{connection.src_port}</TableCell>
              <TableCell className="font-mono text-xs">{connection.dst_ip}:{connection.dst_port}</TableCell>
              <TableCell>{connection.proto.toUpperCase()}</TableCell>
            </TableRow>)}</TableBody>
          </Table> : <p className="text-sm text-muted-foreground">{t("analysis_no_records")}</p>}
          <Pagination offset={data.details[0].offset} limit={data.details[0].limit} total={data.details[0].total}
            loading={resource.loading} onChange={(value) => { setSelected(data.session!.id); setRecordOffset(value); }} />
          {data.details[1].total > 0 && <>
            <h3 className="text-sm font-medium">{t("analysis_alerts")}</h3>
            {data.details[1].items.map((alert) => <div key={alert.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span><Badge variant="outline">{t(`severity_${alert.severity}`)}</Badge> {attackKeys[alert.attack_type] ? t(attackKeys[alert.attack_type]) : alert.attack_type}</span>
              <Button variant="ghost" size="sm" aria-label={t("finding_inspect", { id: alert.id })} onClick={() => inspect(alert)}>{t("finding_details")}</Button>
            </div>)}
            <Pagination offset={data.details[1].offset} limit={data.details[1].limit} total={data.details[1].total}
              loading={resource.loading} onChange={(value) => { setSelected(data.session!.id); setAlertOffset(value); }} />
          </>}
          {data.session.detector_status === "configured" && data.session.status === "completed" && data.details[1].total === 0 && <p className="text-sm text-muted-foreground">{t(data.session.records_prepared ? "analysis_no_findings" : "analysis_no_new_connections")}</p>}
          </>}
        </div>}
      </CardContent>
    </Card>
  );
}
