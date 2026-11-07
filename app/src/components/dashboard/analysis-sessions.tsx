import { useCallback, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { LoadingRegion } from "@/components/loading-region";
import { Pagination } from "@/components/pagination";
import { DataState } from "@/components/data-state";
import { useResource } from "@/hooks/use-resource";
import { useI18n, type TranslationKey } from "@/i18n";
import { api } from "@/services/api";
import { attackKeys } from "@/lib/display";
import type { Alert, SensorFileIssue } from "@/services/types";

const issueLabels: Record<SensorFileIssue["code"], TranslationKey> = {
  corrupt_file: "analysis_file_corrupt",
  unreadable_file: "analysis_file_unreadable",
  oversized_file: "analysis_file_oversized",
  file_unavailable: "analysis_file_unavailable",
};

const errorLabels: Record<string, TranslationKey> = {
  invalid_records: "analysis_error_records",
  sensor_unavailable: "analysis_error_sensor",
  cursor_conflict: "analysis_error_conflict",
  detector_failed: "analysis_error_detector",
  processing_failed: "analysis_error_processing",
  server_restarted: "analysis_error_restart",
  request_interrupted: "analysis_error_interrupted",
};

export function AnalysisSessions({ inspect, refreshVersion = 0 }: { inspect: (alert: Alert) => void; refreshVersion?: number }) {
  const { t, language } = useI18n();
  const [selected, setSelected] = useState<string | null>(null);
  const [recordOffset, setRecordOffset] = useState(0);
  const [alertOffset, setAlertOffset] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const load = useCallback(async (signal: AbortSignal) => {
    const history = await api.getAnalysisSessions(signal);
    const session = selected && history.total > 0
      ? await api.getAnalysisSession(selected, signal)
      : history.items[0] ?? null;
    const details = session && expanded ? await Promise.all([
      api.getAnalysisConnections(session.id, recordOffset, signal),
      api.getAnalysisAlerts(session.id, alertOffset, signal),
    ]) : null;
    return { history, session, details, query: { selected, recordOffset, alertOffset, refreshVersion } };
  }, [selected, recordOffset, alertOffset, expanded, refreshVersion]);
  const resource = useResource(load);
  const data = resource.data;
  const sessionLoading = resource.loading && (!data || data.query.selected !== selected || data.query.refreshVersion !== refreshVersion);
  const recordsLoading = resource.loading && (sessionLoading || !data?.details || data.query.recordOffset !== recordOffset);
  const alertsLoading = resource.loading && (sessionLoading || !data?.details || data.query.alertOffset !== alertOffset);
  return (
    <Card>
      <CardHeader><CardTitle>{t("analysis_sessions")}</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <DataState loading={resource.loading && !data} error={resource.error} hasData={!!data} retry={() => { void resource.refresh(); }} />
        {data && !data.history.items.length && <p className="text-sm text-muted-foreground">{t("analysis_no_sessions")}</p>}
        {data && data.history.items.length > 0 && <>
          <div className="flex flex-wrap gap-2" role="group" aria-label={t("analysis_sessions")}>
            {data.history.items.map((session) => <Button
              key={session.id} variant={session.id === (selected ?? data.session?.id) ? "secondary" : "outline"}
              size="sm" aria-pressed={session.id === (selected ?? data.session?.id)} disabled={resource.loading}
              className={session.id === (selected ?? data.session?.id) ? "border border-transparent" : "border"}
              aria-label={t("analysis_select", { id: session.id })}
              onClick={() => { setSelected(session.id); setRecordOffset(0); setAlertOffset(0); setExpanded(true); }}
            >
              <span className="font-mono">{session.id.slice(0, 8)}</span>
              {t(`analysis_status_${session.status}`)}
            </Button>)}
          </div>
        </>}
        {data?.session && data.session.file_issues.length > 0 && <Card role="status">
          <CardHeader><CardTitle>{t("analysis_skipped_files", { count: data.session.file_issues.length })}</CardTitle></CardHeader>
          <CardContent className="space-y-2"><LoadingRegion loading={sessionLoading}>
            <ul className="max-h-48 space-y-2 overflow-auto text-sm">
              {data.session.file_issues.map((issue, index) => <li key={`${issue.file}-${index}`}>
                <span className="break-all font-mono">{issue.file}</span>{" "}
                <Badge variant="outline">{t(issueLabels[issue.code])}</Badge>
                {issue.offset !== null && <span className="text-muted-foreground"> {t("analysis_skip_offset", { offset: issue.offset })}</span>}
              </li>)}
            </ul>
          </LoadingRegion></CardContent>
        </Card>}
        {data?.session && <div className="space-y-3 border-t pt-4">
          <LoadingRegion loading={sessionLoading} contentClassName="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Badge variant={data.session.status === "completed" ? "success" : data.session.status === "running" ? "default" : "destructive"}>
              {t(`analysis_status_${data.session.status}`)}
            </Badge>
            {data.session.status === "running" && <LoadingOrb size={20} text={t("btn_analyzing")} />}
          </div>
          <dl className="grid grid-cols-1 gap-3 py-2 sm:grid-cols-3" aria-live="polite">
            {[
              { label: t("analysis_imported"), value: data.session.new_connections_ingested, color: "text-primary", background: "bg-primary/10" },
              { label: t("analysis_prepared_count"), value: data.session.records_prepared, color: "text-low", background: "bg-low/10" },
              { label: t("analysis_findings_count"), value: data.session.new_alerts_detected, color: "text-medium", background: "bg-medium/10" },
            ].map(item => <div key={item.label} className={`rounded-lg px-4 py-3 ${item.background}`}>
              <dt className="text-xs text-muted-foreground">{item.label}</dt>
              <dd className={`mt-1 text-2xl font-semibold tabular-nums ${item.color}`}>{item.value}</dd>
            </div>)}
          </dl>
          <dl className="flex flex-wrap gap-x-8 gap-y-3 pb-2 text-xs">
            <div><dt className="text-muted-foreground">{t("analysis_started_at")}</dt><dd className="mt-1">{new Date(data.session.started_at).toLocaleString(language === "ro" ? "ro-RO" : "en-GB")}</dd></div>
            <div><dt className="text-muted-foreground">{t("analysis_source_label")}</dt><dd className="mt-1">{t(`analysis_source_${data.session.source}`)}</dd></div>
            {data.session.detector_status === "configured" && <div><dt className="text-muted-foreground">{t("analysis_model_label")}</dt><dd className="mt-1">{data.session.detector_name.startsWith("random_forest") ? t("model_random_forest") : data.session.detector_name}</dd></div>}
            {data.session.finished_at && <>
              <div><dt className="text-muted-foreground">{t("analysis_duration")}</dt><dd className="mt-1 tabular-nums">{t("analysis_seconds", { seconds: Math.max(0, (new Date(data.session.finished_at).getTime() - new Date(data.session.started_at).getTime()) / 1000).toFixed(1) })}</dd></div>
              <div><dt className="text-muted-foreground">{t("analysis_finished_at")}</dt><dd className="mt-1">{new Date(data.session.finished_at).toLocaleString(language === "ro" ? "ro-RO" : "en-GB")}</dd></div>
            </>}
          </dl>
          {data.session.detector_status === "not_configured" && <p className="text-sm text-muted-foreground">{t("analysis_no_detector")}</p>}
          {data.session.error_code && <p role="alert" className="text-sm text-destructive">{t(errorLabels[data.session.error_code] ?? "analysis_error_processing")}</p>}
          </LoadingRegion>
          <Button variant="outline" size="sm" aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>{t(expanded ? "analysis_hide_details" : "analysis_show_details")}</Button>
          {expanded && <>
          <h3 className="text-sm font-medium">{t("analysis_records")}</h3>
          <LoadingRegion loading={recordsLoading}>
          {data.details && <>
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
          </>}
          </LoadingRegion>
          {data.details && <Pagination offset={data.details[0].offset} limit={data.details[0].limit} total={data.details[0].total}
            loading={resource.loading} onChange={setRecordOffset} />}
          {data.details && data.details[1].total > 0 && <>
            <h3 className="text-sm font-medium">{t("analysis_alerts")}</h3>
            <LoadingRegion loading={alertsLoading} contentClassName="space-y-2">
            {data.details[1].items.map((alert) => <div key={alert.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span><Badge variant="outline">{t(`severity_${alert.severity}`)}</Badge> {attackKeys[alert.attack_type] ? t(attackKeys[alert.attack_type]) : alert.attack_type}</span>
              <Button variant="ghost" size="sm" aria-label={t("finding_inspect", { id: alert.id })} onClick={() => inspect(alert)}>{t("finding_details")}</Button>
            </div>)}
            </LoadingRegion>
            <Pagination offset={data.details[1].offset} limit={data.details[1].limit} total={data.details[1].total}
              loading={resource.loading} onChange={setAlertOffset} />
          </>}
          {data.details && !resource.loading && data.session.detector_status === "configured" && data.session.status === "completed" && data.details[1].total === 0 && <p className="text-sm text-muted-foreground">{t(data.session.records_prepared ? "analysis_no_findings" : "analysis_no_new_connections")}</p>}
          </>}
        </div>}
      </CardContent>
    </Card>
  );
}
