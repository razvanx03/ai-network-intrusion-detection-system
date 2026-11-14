import { ServerNameHeading } from "@/components/server-name-heading";
import { useCallback, useState } from "react";
import { Link } from "@/router";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { LoadingRegion } from "@/components/loading-region";
import { Pagination } from "@/components/pagination";
import { DataState } from "@/components/data-state";
import { SessionSelector } from "@/components/dashboard/session-selector";
import { useResource } from "@/hooks/use-resource";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import { issueLabels, errorLabels } from "@/lib/analysis-labels";

export function AnalysisSessions({ refreshVersion = 0, includeArchived = false, archivedOnly = false, alertsOnly = false, hideTitle = false }: { refreshVersion?: number; includeArchived?: boolean; archivedOnly?: boolean; alertsOnly?: boolean; hideTitle?: boolean }) {
  const { t, language } = useI18n();
  const [selected, setSelected] = useState<string | null>(null);
  const [recordOffset, setRecordOffset] = useState(0);
  const [recordLimit, setRecordLimit] = useState(20);
  const [expanded, setExpanded] = useState(false);
  const scope = `${archivedOnly}:${alertsOnly}`;
  const [previousScope, setPreviousScope] = useState(scope);
  if (previousScope !== scope) {
    setPreviousScope(scope);
    setSelected(null);
    setRecordOffset(0);
  }
  const load = useCallback(async (signal: AbortSignal) => {
    const history = await api.getAnalysisSessions(signal, includeArchived, archivedOnly, alertsOnly);
    const session = selected && history.items.some(item => item.id === selected)
      ? await api.getAnalysisSession(selected, signal, includeArchived)
      : history.items[0] ?? null;
    const details = session && expanded ? await api.getAnalysisConnections(session.id, recordOffset, signal, includeArchived, recordLimit) : null;
    return { history, session, details, query: { selected, recordOffset, recordLimit, refreshVersion } };
  }, [selected, recordOffset, recordLimit, expanded, refreshVersion, includeArchived, archivedOnly, alertsOnly]);
  const cacheKey = `sessions:${includeArchived}:${archivedOnly}:${alertsOnly}:${selected}:${recordOffset}:${recordLimit}:${expanded}`;
  const resource = useResource(load, true, refreshVersion, cacheKey);
  const data = resource.data;
  const sessionLoading = resource.loading && (!data || data.query.selected !== selected || data.query.refreshVersion !== refreshVersion);
  const recordsLoading = resource.loading && (sessionLoading || !data?.details || data.query.recordOffset !== recordOffset || data.query.recordLimit !== recordLimit);
  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
        {!hideTitle && <CardTitle>{t("analysis_sessions")}</CardTitle>}
        <Button asChild variant="outline" size="sm" className="ml-auto"><Link to="/import-problems">{t("import_problems_history")}</Link></Button>
      </CardHeader>
      <CardContent className={`space-y-4 ${hideTitle ? "pt-6" : ""}`}>
        <DataState loading={resource.loading && !data} error={resource.error} hasData={!!data} retry={() => { void resource.refresh(); }} />
        {data && !data.history.items.length && <p className="text-sm text-muted-foreground">{t("analysis_no_sessions")}</p>}
        {data && data.history.items.length > 0 && <>
          <SessionSelector sessions={data.history.items} selectedId={selected ?? data.session?.id}
            loading={resource.loading} includeArchived={includeArchived}
            onSelect={(id) => { setSelected(id); setRecordOffset(0); setExpanded(true); }} />
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
          <dl className="grid grid-cols-1 gap-3 py-2 sm:grid-cols-2" aria-live="polite">
            {[
              { label: t("analysis_imported"), value: data.session.new_connections_ingested, color: "text-primary", background: "bg-primary/10" },
              { label: t("analysis_findings_count"), value: data.session.new_alerts_detected, color: "text-medium", background: "bg-medium/10" },
            ].map(item => <div key={item.label} className={`rounded-lg px-4 py-3 ${item.background}`}>
              <dt className="text-xs text-muted-foreground">{item.label}</dt>
              <dd className={`mt-1 text-2xl font-semibold tabular-nums ${item.color}`}>{item.value}</dd>
            </div>)}
          </dl>
          <dl className="flex flex-wrap gap-x-8 gap-y-3 pb-2 text-xs">
            <div><dt className="text-muted-foreground">{t("analysis_started_at")}</dt><dd className="mt-1">{new Date(data.session.started_at).toLocaleString(language === "ro" ? "ro-RO" : "en-GB")}</dd></div>
            <div><dt className="text-muted-foreground">{t("analysis_source_label")}</dt><dd className="mt-1">{t(`analysis_source_${data.session.source}`)}</dd></div>
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
          {data.details.items.length ? <Table>
            <TableHeader><TableRow>
              <TableHead>{t("th_uid")}</TableHead><TableHead>{t("analysis_origin")}</TableHead>
              <TableHead>{t("th_destination")}</TableHead><TableHead><ServerNameHeading /></TableHead><TableHead>{t("th_protocol")}</TableHead>
            </TableRow></TableHeader>
            <TableBody>{data.details.items.map(({ connection, file }) => <TableRow key={connection.id}>
              <TableCell className="font-mono text-xs" title={file ?? undefined}>{connection.uid}</TableCell>
              <TableCell className="font-mono text-xs">{connection.src_ip}:{connection.src_port}</TableCell>
              <TableCell className="font-mono text-xs">{connection.dst_ip}:{connection.dst_port}</TableCell>
              <TableCell className="max-w-64 break-all text-xs">{connection.server_name ?? "—"}</TableCell>
              <TableCell>{connection.proto.toUpperCase()}</TableCell>
            </TableRow>)}</TableBody>
          </Table> : <p className="text-sm text-muted-foreground">{t("analysis_no_records")}</p>}
          </>}
          </LoadingRegion>
          {data.details && <Pagination offset={data.details.offset} limit={data.details.limit} total={data.details.total}
            loading={resource.loading} onChange={setRecordOffset}
            onLimitChange={(limit) => { setRecordLimit(limit); setRecordOffset(0); }} />}
          </>}
        </div>}
      </CardContent>
    </Card>
  );
}
