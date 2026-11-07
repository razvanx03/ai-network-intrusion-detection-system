import { useCallback, useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableHead, TableHeader, TableRow, TableBody, TableCell } from "@/components/ui/table";
import { DataState } from "@/components/data-state";
import { LoadingRegion } from "@/components/loading-region";
import { Pagination } from "@/components/pagination";
import { useResource } from "@/hooks/use-resource";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import { attackKeys, descriptionKeys } from "@/lib/display";
import type { Alert, Connection, Page } from "@/services/types";

export function FindingDetails({ alert, close, includeArchived = false }: { alert: Alert; close: () => void; includeArchived?: boolean }) {
  const { t, language } = useI18n();
  const [offset, setOffset] = useState(0);
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => { panel.current?.scrollIntoView({ block: "start", behavior: "smooth" }); }, []);
  const load = useCallback(async (signal: AbortSignal): Promise<Page<Connection>> => {
    if (!alert.analysis_session_id) return { items: [], total: 0, limit: 10, offset: 0 };
    return api.getAlertConnections(alert.analysis_session_id, alert.id, offset, signal, includeArchived);
  }, [alert.id, alert.analysis_session_id, offset, includeArchived]);
  const resource = useResource(load);
  return <Card ref={panel} className="scroll-mt-32">
    <CardHeader className="flex flex-row items-center justify-between gap-3"><CardTitle>{t("finding_inspect", { id: alert.id })}</CardTitle><Button variant="ghost" size="sm" onClick={close}>{t("close")}</Button></CardHeader>
    <CardContent className="space-y-4">
      <p className="text-sm font-medium">{attackKeys[alert.attack_type] ? t(attackKeys[alert.attack_type]) : alert.attack_type}</p>
      <p className="max-w-prose text-sm text-muted-foreground">{descriptionKeys[alert.description] ? t(descriptionKeys[alert.description]) : alert.description}</p>
      <dl className="grid gap-3 text-sm sm:grid-cols-3">
        <div><dt className="text-muted-foreground">{t("finding_time")}</dt><dd>{new Date(alert.timestamp).toLocaleString(language === "ro" ? "ro-RO" : "en-GB")}</dd></div>
        <div><dt className="text-muted-foreground">{t("model_score")}</dt><dd className="tabular-nums">{alert.confidence.toFixed(3)}</dd></div>
        <div><dt className="text-muted-foreground">{t("th_status")}</dt><dd>{t(`status_${alert.status}`)}</dd></div>
      </dl>
      <p className="max-w-prose text-xs text-muted-foreground">{t("model_score_help")}</p>
      {alert.mitre_technique && <p className="text-sm">{t("th_mitre")}: {alert.mitre_technique}</p>}
      <h3 className="text-sm font-medium">{t("finding_evidence")}</h3>
      {!alert.analysis_session_id ? <p className="text-sm text-muted-foreground">{t("finding_legacy_evidence")}</p> : <>
        <DataState loading={false} error={resource.error} hasData={!!resource.data} retry={() => { void resource.refresh(); }} />
        <LoadingRegion loading={resource.loading}>
        {resource.data && (resource.data.items.length ? <Table>
          <TableHeader><TableRow><TableHead>{t("th_uid")}</TableHead><TableHead>{t("th_source")}</TableHead><TableHead>{t("th_destination")}</TableHead><TableHead>{t("th_protocol")}</TableHead><TableHead>{t("th_duration")}</TableHead><TableHead>{t("th_bytes")}</TableHead><TableHead>{t("th_packets")}</TableHead><TableHead>{t("th_conn_state")}</TableHead></TableRow></TableHeader>
          <TableBody>{resource.data.items.map(connection => <TableRow key={connection.id}>
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
        {resource.data && <Pagination offset={resource.data.offset} limit={resource.data.limit} total={resource.data.total} loading={resource.loading} onChange={setOffset} />}
      </>}
    </CardContent>
  </Card>;
}
