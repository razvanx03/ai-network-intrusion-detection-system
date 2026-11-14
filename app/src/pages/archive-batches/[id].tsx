import { useCallback, useId, useState } from "react";
import { ArrowLeft, Archive } from "lucide-react";
import { FilterButton } from "@/components/filter-button";
import { Link, useParams } from "@/router";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { TableHeader, TableHead, TableBody, TableRow, TableCell } from "@/components/ui/table";
import { Modal } from "@/components/modal";
import { DataState } from "@/components/data-state";
import { PaginatedTable } from "@/components/paginated-table";
import { Pagination } from "@/components/pagination";
import { LoadingRegion } from "@/components/loading-region";
import { TrafficHeaders, TrafficCells, trafficTableClassName } from "@/components/traffic-columns";
import { ProtocolSelect } from "@/components/protocol-select";
import { ConnectionContext } from "@/components/connection-context";
import { AlertStatusBadge } from "@/components/alert-status-badge";
import { useResource } from "@/hooks/use-resource";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import { issueLabels, errorLabels } from "@/lib/analysis-labels";
import type { AnalysisSession, ArchiveBatch, Connection } from "@/services/types";

export default function ArchiveBatchPage() {
  const { id } = useParams("/archive-batches/:id");
  const { t, language } = useI18n();
  const load = useCallback((signal: AbortSignal) => api.getArchive(id, signal), [id]);
  const resource = useResource(load, true, 0, `archive:${id}`);
  const batch = resource.data?.id === id ? resource.data : null;
  const date = (value: string) => new Date(value).toLocaleString(language === "ro" ? "ro-RO" : "en-GB");
  return <div className="space-y-6 [overflow-anchor:none]">
    <div className="flex flex-wrap items-center gap-3">
      <Button asChild variant="outline" size="sm"><Link to="/all-data"><ArrowLeft className="size-4" />{t("archive_back")}</Link></Button>
      {batch && <>
        <h1 className="flex items-center gap-2 text-xl font-bold"><Archive className="size-5 shrink-0 text-primary" />{t("archive_batch_title", { date: date(batch.created_at) })}</h1>
        <Badge variant={batch.restored_at ? "success" : "secondary"}>{t(batch.restored_at ? "archive_restored" : "archive_archived")}</Badge>
        {batch.restored_at && <span className="text-sm text-muted-foreground">{t("archive_restored_at")}: {date(batch.restored_at)}</span>}
      </>}
    </div>
    <DataState loading={resource.loading && !batch} error={resource.error} hasData={!!batch} retry={() => { void resource.refresh(); }} />
    {batch && <>
        <dl className="flex flex-wrap gap-x-8 gap-y-3 border-y py-4 text-sm">
          {(["connections", "alerts", "sessions"] as const).map((field, index) => <div key={field} className="flex items-baseline gap-2">
            <dt className="text-muted-foreground">{t((["archive_traffic", "archive_alerts", "archive_sessions"] as const)[index])}</dt>
            <dd className="font-semibold tabular-nums">{batch[field].toLocaleString(language)}</dd>
          </div>)}
        </dl>
      {batch.snapshot_version === 1 ? <>
        <BatchContents key={id} batch={batch} />
      </> : <p className="max-w-3xl rounded-lg border bg-card p-5 text-sm leading-relaxed text-muted-foreground">{t("archive_snapshot_unavailable")}</p>}
    </>}
  </div>;
}

function BatchContents({ batch }: { batch: ArchiveBatch }) {
  const { t, language } = useI18n();
  const [view, setView] = useState<"traffic" | "sessions">("traffic");
  const [protocols, setProtocols] = useState<string[]>([]);
  const [alertsOnly, setAlertsOnly] = useState(false);
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(20);
  const alertsId = useId();
  const reset = () => setOffset(0);
  return <div className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap gap-2" role="group" aria-label={t("archive_views")}>
        {(["traffic", "sessions"] as const).map(item => <Button key={item} variant="outline" aria-pressed={view === item} className={view === item ? "bg-accent text-accent-foreground" : ""} onClick={() => { setView(item); reset(); }}>{t(`archive_${item}`)}</Button>)}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Popover modal={false}><PopoverTrigger asChild><FilterButton activeCount={Number(alertsOnly)} disabled={view !== "traffic"} /></PopoverTrigger>
          <PopoverContent align="end" collisionPadding={16} className="w-72"><div className="flex items-center justify-between gap-3"><Label htmlFor={alertsId}>{t("data_alerts_only")}</Label><Switch id={alertsId} checked={alertsOnly} onCheckedChange={checked => { setAlertsOnly(checked); reset(); }} /></div></PopoverContent>
        </Popover>
        <ProtocolSelect archiveBatchId={batch.id} selected={protocols} disabled={view !== "traffic"} onChange={values => { setProtocols(values); reset(); }} />
      </div>
    </div>
    <div className="min-h-[calc(100dvh-8rem)] space-y-4">
      {view === "traffic" && <>
        {session && <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-sm">
          <span>{t("archive_session_scope", { date: new Date(session.started_at).toLocaleString(language === "ro" ? "ro-RO" : "en-GB") })}</span>
          <Button variant="outline" size="sm" onClick={() => { setSession(null); reset(); }}>{t("archive_clear_session")}</Button>
        </div>}
        <BatchTraffic batchId={batch.id} protocols={protocols} alertsOnly={alertsOnly} sessionId={session?.id} offset={offset} limit={limit} setOffset={setOffset} setLimit={value => { setLimit(value); reset(); }} />
      </>}
      {view === "sessions" && <BatchSessions batchId={batch.id} offset={offset} setOffset={setOffset} showTraffic={item => { setSession(item); setView("traffic"); setProtocols([]); setAlertsOnly(false); reset(); }} />}
    </div>
  </div>;
}

function BatchTraffic({ batchId, protocols, alertsOnly, sessionId, offset, limit, setOffset, setLimit }: {
  batchId: string; protocols: string[]; alertsOnly: boolean; sessionId?: string; offset: number; limit: number;
  setOffset: (value: number) => void; setLimit: (value: number) => void;
}) {
  const { t, language } = useI18n();
  const [selected, setSelected] = useState<Connection | null>(null);
  const load = useCallback((signal: AbortSignal) => api.getArchiveConnections(batchId, { offset, limit, protocols, alerts_only: alertsOnly, session_id: sessionId }, signal), [batchId, offset, limit, protocols, alertsOnly, sessionId]);
  const resource = useResource(load, true, 0, `batch_traffic:${batchId}:${offset}:${limit}:${protocols.join(",")}:${alertsOnly}:${sessionId}`);
  return <>
    <Card><CardContent className="pt-6">
      <DataState loading={resource.loading && !resource.data} error={resource.error} hasData={!!resource.data} retry={() => { void resource.refresh(); }} />
      {resource.data && <PaginatedTable {...resource.data} tableClassName={trafficTableClassName} hasRows={!!resource.data.items.length} emptyMessage={t("archive_snapshot_empty")} loading={resource.loading} dataLoading={resource.loading} onChange={setOffset} onLimitChange={setLimit}>
        <TableHeader><TableRow><TrafficHeaders /><TableHead>{t("th_action")}</TableHead></TableRow></TableHeader>
        <TableBody>{resource.data.items.map(connection => <TableRow key={connection.id}><TrafficCells connection={connection} /><TableCell><Button variant="outline" size="sm" aria-label={t("context_inspect", { uid: connection.uid })} onClick={() => setSelected(connection)}>{t("finding_details")}</Button></TableCell></TableRow>)}</TableBody>
      </PaginatedTable>}
    </CardContent></Card>
    {selected && <Modal open title={t("context_title")} onOpenChange={open => { if (!open) setSelected(null); }}>
      <div className="space-y-6">
        <dl className="text-sm"><dt className="text-muted-foreground">{t("finding_time")}</dt><dd>{new Date(selected.ts * 1000).toLocaleString(language === "ro" ? "ro-RO" : "en-GB")}</dd></dl>
        <ConnectionContext connection={selected} archiveBatchId={batchId} /><SavedAlerts batchId={batchId} connection={selected} />
      </div>
    </Modal>}
  </>;
}

function SavedAlerts({ batchId, connection }: { batchId: string; connection: Connection }) {
  const { t, language } = useI18n();
  const [offset, setOffset] = useState(0);
  const load = useCallback((signal: AbortSignal) => api.getArchiveAlerts(batchId, connection.id, offset, signal), [batchId, connection.id, offset]);
  const resource = useResource(load, true, 0, `batch_alerts:${batchId}:${connection.id}:${offset}`);
  return <section className="space-y-3 border-t pt-4">
    <h3 className="text-sm font-semibold">{t("archive_saved_alerts")}</h3>
    <DataState loading={false} error={resource.error} hasData={!!resource.data} retry={() => { void resource.refresh(); }} />
    <LoadingRegion loading={resource.loading}>
      {resource.data && (resource.data.items.length ? <dl className="space-y-3">{resource.data.items.map(alert => <div key={alert.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-muted/30 p-3 text-sm">
        <dt>{new Date(alert.timestamp).toLocaleString(language === "ro" ? "ro-RO" : "en-GB")}</dt>
        <dd>{t("model_score")}: <span className="tabular-nums">{alert.confidence.toFixed(3)}</span></dd><dd><AlertStatusBadge status={alert.status} /></dd>
      </div>)}</dl> : <p className="text-sm text-muted-foreground">{t("archive_no_saved_alerts")}</p>)}
    </LoadingRegion>
    {resource.data && resource.data.total > resource.data.limit && <Pagination {...resource.data} loading={resource.loading} onChange={setOffset} />}
  </section>;
}

function BatchSessions({ batchId, offset, setOffset, showTraffic }: { batchId: string; offset: number; setOffset: (value: number) => void; showTraffic: (session: AnalysisSession) => void }) {
  const { t, language } = useI18n();
  const [selected, setSelected] = useState<AnalysisSession | null>(null);
  const load = useCallback((signal: AbortSignal) => api.getArchiveSessions(batchId, offset, signal), [batchId, offset]);
  const resource = useResource(load, true, 0, `batch_sessions:${batchId}:${offset}`);
  const date = (value: string | null) => value ? new Date(value).toLocaleString(language === "ro" ? "ro-RO" : "en-GB") : "—";
  return <>
    <Card><CardContent className="pt-6">
      <DataState loading={resource.loading && !resource.data} error={resource.error} hasData={!!resource.data} retry={() => { void resource.refresh(); }} />
      {resource.data && <PaginatedTable {...resource.data} hasRows={!!resource.data.items.length} emptyMessage={t("archive_snapshot_empty")} loading={resource.loading} dataLoading={resource.loading} onChange={setOffset}>
        <TableHeader><TableRow><TableHead>{t("analysis_started_at")}</TableHead><TableHead>{t("analysis_source_label")}</TableHead><TableHead>{t("th_status")}</TableHead><TableHead>{t("analysis_imported")}</TableHead><TableHead>{t("analysis_findings_count")}</TableHead><TableHead>{t("th_action")}</TableHead></TableRow></TableHeader>
        <TableBody>{resource.data.items.map(session => <TableRow key={session.id}>
          <TableCell className="whitespace-nowrap">{date(session.started_at)}</TableCell><TableCell>{t(`analysis_source_${session.source}`)}</TableCell>
          <TableCell><Badge variant={session.status === "completed" ? "success" : "destructive"}>{t(`analysis_status_${session.status}`)}</Badge></TableCell>
          <TableCell>{session.new_connections_ingested}</TableCell><TableCell>{session.new_alerts_detected}</TableCell>
          <TableCell><div className="flex gap-2"><Button variant="outline" size="sm" onClick={() => setSelected(session)}>{t("finding_details")}</Button><Button variant="outline" size="sm" onClick={() => showTraffic(session)}>{t("archive_session_traffic")}</Button></div></TableCell>
        </TableRow>)}</TableBody>
      </PaginatedTable>}
    </CardContent></Card>
    {selected && <Modal open title={t("archive_session_details")} onOpenChange={open => { if (!open) setSelected(null); }}>
      <div className="space-y-5">
        <Badge variant={selected.status === "completed" ? "success" : "destructive"}>{t(`analysis_status_${selected.status}`)}</Badge>
        <dl className="grid gap-4 text-sm sm:grid-cols-3">
          <div><dt className="text-muted-foreground">{t("analysis_started_at")}</dt><dd>{date(selected.started_at)}</dd></div>
          <div><dt className="text-muted-foreground">{t("analysis_finished_at")}</dt><dd>{date(selected.finished_at)}</dd></div>
          <div><dt className="text-muted-foreground">{t("analysis_source_label")}</dt><dd>{t(`analysis_source_${selected.source}`)}</dd></div>
          <div><dt className="text-muted-foreground">{t("analysis_imported")}</dt><dd>{selected.new_connections_ingested}</dd></div>
          <div><dt className="text-muted-foreground">{t("analysis_findings_count")}</dt><dd>{selected.new_alerts_detected}</dd></div>
        </dl>
        {selected.error_code && <p className="text-sm text-destructive">{t(errorLabels[selected.error_code] ?? "analysis_error_processing")}</p>}
        {selected.file_issues.length > 0 && <section className="space-y-3 border-t pt-4"><h3 className="text-sm font-semibold">{t("analysis_skipped_files", { count: selected.file_issues.length })}</h3>
          <ul className="space-y-2 text-sm">{selected.file_issues.map((issue, index) => <li key={index} className="space-y-1"><p className="break-all font-mono text-xs">{issue.file}</p><Badge variant="outline">{t(issueLabels[issue.code])}</Badge></li>)}</ul>
        </section>}
        <Button variant="outline" onClick={() => { showTraffic(selected); setSelected(null); }}>{t("archive_session_traffic")}</Button>
      </div>
    </Modal>}
  </>;
}
