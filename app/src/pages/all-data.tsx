import { useCallback, useId, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Link } from "@/router";
import { Archive, ArchiveRestore } from "lucide-react";
import { FilterButton } from "@/components/filter-button";
import { Button } from "@/components/ui/button";
import { InfoTooltip } from "@/components/info-tooltip";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { TableHeader, TableHead, TableBody, TableRow, TableCell } from "@/components/ui/table";
import { PaginatedTable } from "@/components/paginated-table";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { ArchiveDataButton } from "@/components/archive-data-button";
import { ConnectionBrowser } from "@/components/connection-browser";
import { AnalysisSessions } from "@/components/dashboard/analysis-sessions";
import { FindingDetails } from "@/components/dashboard/finding-details";
import { ProtocolSelect } from "@/components/protocol-select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { DataState, OperationNotice, type Notice } from "@/components/data-state";
import { useSensorSync } from "@/hooks/use-sensor-sync";
import { clearResourceCache, useResource } from "@/hooks/use-resource";
import { useUrlPagination } from "@/hooks/use-url-pagination";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import { errorKey } from "@/services/errors";
import type { Alert } from "@/services/types";

export default function AllDataPage() {
  const { t, language } = useI18n();
  const sync = useSensorSync();
  const [view, setView] = useState<"traffic" | "sessions">("traffic");
  const [archivedOnly, setArchivedOnly] = useState(false);
  const switchId = useId();
  const alertsSwitchId = useId();
  const [alertsOnly, setAlertsOnly] = useState(false);
  const [protocols, setProtocols] = useState<string[]>([]);
  const [, setSearchParams] = useSearchParams();
  const resetDataPage = () => {
    setSelected(null);
    setSearchParams(previous => {
      const next = new URLSearchParams(previous);
      next.delete("archived_page");
      return next;
    });
  };
  const { offset, setOffset } = useUrlPagination({ pageParam: "batch_page" });
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [selected, setSelected] = useState<Alert | null>(null);
  const lock = useRef(false);
  const load = useCallback((signal: AbortSignal) => api.getArchives(offset, signal), [offset]);
  const cacheKey = `archives:${offset}`;
  const resource = useResource(load, true, version, cacheKey);
  const change = async (id?: string) => {
    if (lock.current) return;
    lock.current = true;
    setBusy(id ?? "archive");
    setNotice(null);
    try {
      if (id) await api.restoreArchive(id);
      else await api.archiveDatabase();
      clearResourceCache();
      setNotice({ key: id ? "archive_restored_done" : "archive_done" });
      setSelected(null);
      setVersion(value => value + 1);
    } catch (error) {
      setNotice({ key: errorKey(error), error: true });
    } finally {
      lock.current = false;
      setBusy(null);
    }
  };
  return <div className="space-y-6 [overflow-anchor:none]">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <h1 className="flex items-center gap-2 text-xl font-bold"><Archive className="size-5 text-primary" />{t("archive_nav")}<InfoTooltip label={t("archive_help_label")} text={t("archive_description")} /></h1>
      <ArchiveDataButton busy={busy === "archive"} disabled={!!busy || resource.loading || sync.syncing} archive={() => { void change(); }} />
    </div>
    <OperationNotice notice={notice} close={() => setNotice(null)} />
    <Card><CardHeader><CardTitle>{t("archive_batches")}</CardTitle></CardHeader><CardContent>
      <DataState loading={resource.loading && !resource.data} error={resource.error} hasData={!!resource.data} retry={() => { void resource.refresh(); }} />
      {resource.data && <PaginatedTable {...resource.data} paginate={resource.data.total > resource.data.limit} hasRows={resource.data.items.length > 0} emptyMessage={t("archive_no_batches")} loading={resource.loading || !!busy} dataLoading={resource.loading} onChange={setOffset}>
        <TableHeader><TableRow><TableHead>{t("archive_created")}</TableHead><TableHead>{t("archive_traffic")}</TableHead><TableHead>{t("archive_alerts")}</TableHead><TableHead>{t("archive_sessions")}</TableHead><TableHead>{t("archive_state")}</TableHead><TableHead>{t("th_action")}</TableHead></TableRow></TableHeader>
        <TableBody>{resource.data.items.map(batch => <TableRow key={batch.id}>
          <TableCell>{new Date(batch.created_at).toLocaleString(language === "ro" ? "ro-RO" : "en-GB")}</TableCell>
          <TableCell>{batch.connections}</TableCell><TableCell>{batch.alerts}</TableCell><TableCell>{batch.sessions}</TableCell>
          <TableCell><Badge variant={batch.restored_at ? "success" : "secondary"}>{t(batch.restored_at ? "archive_restored" : "archive_archived")}</Badge></TableCell>
          <TableCell><div className="flex items-center gap-2"><Button asChild variant="outline" size="sm"><Link to="/archive-batches/:id" params={{ id: batch.id }}>{t("archive_view_batch")}</Link></Button><Button variant="outline" size="sm" disabled={!!busy || sync.syncing || !!batch.restored_at} aria-label={t("archive_restore_batch", { id: batch.id.slice(0, 8) })} onClick={() => { void change(batch.id); }}>
            {busy === batch.id ? <LoadingOrb size={20} text={t("archive_restoring")} /> : <><ArchiveRestore className="size-4" />{t("archive_restore")}</>}
          </Button></div></TableCell>
        </TableRow>)}</TableBody>
      </PaginatedTable>}
    </CardContent></Card>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label={t("archive_views")}>
        {(["traffic", "sessions"] as const).map(item => <Button key={item} variant="outline" className={item === view ? "bg-accent text-accent-foreground" : ""} aria-pressed={item === view} onClick={() => { setView(item); setSelected(null); }}>{t(`archive_${item}`)}</Button>)}
        <span className="text-sm text-muted-foreground">{t(archivedOnly ? "archive_only_note" : "traffic_including_archived")}</span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Popover modal={false}><PopoverTrigger asChild><FilterButton activeCount={Number(alertsOnly) + Number(archivedOnly)} /></PopoverTrigger>
          <PopoverContent align="end" collisionPadding={16} className="w-72 space-y-4">
            <div className="flex items-center justify-between gap-3"><Label htmlFor={alertsSwitchId}>{t("data_alerts_only")}</Label>
              <Switch id={alertsSwitchId} checked={alertsOnly} onCheckedChange={checked => { setAlertsOnly(checked); resetDataPage(); }} />
            </div>
            <div className="flex items-center justify-between gap-3"><Label htmlFor={switchId}>{t("archive_hide_current")}</Label>
              <Switch id={switchId} checked={archivedOnly} onCheckedChange={checked => { setArchivedOnly(checked); resetDataPage(); }} />
            </div>
          </PopoverContent>
        </Popover>
        <ProtocolSelect selected={protocols} includeArchived disabled={view === "sessions"} onChange={values => { setProtocols(values); resetDataPage(); }} />
      </div>
    </div>
    <div className="min-h-[calc(100dvh-8rem)]">
      {view === "traffic" && <ConnectionBrowser includeArchived archivedOnly={archivedOnly} alertsOnly={alertsOnly} selectedProtocols={protocols} hideProtocolFilter refreshVersion={version} />}
      {view === "sessions" && <AnalysisSessions includeArchived archivedOnly={archivedOnly} alertsOnly={alertsOnly} hideTitle refreshVersion={version} inspect={setSelected} />}
    </div>
    {selected && <FindingDetails key={selected.id} alert={selected} includeArchived close={() => setSelected(null)} />}
  </div>;
}
