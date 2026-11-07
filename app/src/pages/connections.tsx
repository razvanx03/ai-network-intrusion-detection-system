import { useCallback, useRef, useState } from "react";
import { Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { DataState, OperationNotice, type Notice } from "@/components/data-state";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { errorKey } from "@/services/errors";
import { PaginatedTable } from "@/components/paginated-table";
import { useResource } from "@/hooks/use-resource";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import { DEFAULT_PAGE_SIZE } from "@/constants";
export default function ConnectionsPage() {
  const { t } = useI18n();
  const [proto, setProto] = useState("");
  const [offset, setOffset] = useState(0);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [selected, setSelected] = useState<number[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const lock = useRef(false);
  const load = useCallback(
    (signal: AbortSignal) =>
      api.getConnections(
        { proto: proto || undefined, limit: pageSize, offset },
        signal,
      ),
    [proto, offset, pageSize],
  );
  const { data, loading, error, refresh } = useResource(load);
  const analyze = async () => {
    if (lock.current || !selected.length) return;
    lock.current = true;
    setAnalyzing(true);
    setNotice(null);
    try {
      const result = await api.analyzeStored(selected);
      setNotice({ key: result.analysis_session.detector_status === "configured" ? "stored_analysis_done" : "analysis_prepared", params: { count: result.analysis_session.records_prepared, prepared: result.analysis_session.records_prepared, conns: 0, alerts: result.new_alerts_detected } });
      setSelected([]);
    } catch (error) {
      setNotice({ key: errorKey(error), error: true });
    } finally {
      lock.current = false;
      setAnalyzing(false);
    }
  };
  const stateBadge = (state: string | null) => {
    const label = state === "SF" ? t("state_SF")
      : state === "S0" ? t("state_S0")
      : state === "REJ" ? t("state_REJ") : state ?? "—";
    return <div className="flex min-w-24 flex-col items-start gap-1">
      <Badge variant="outline" className="whitespace-nowrap">{state ?? "—"}</Badge>
      {(state === "SF" || state === "S0" || state === "REJ") && <span className="max-w-32 text-xs leading-4 text-muted-foreground">{label}</span>}
    </div>;
  };
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="flex items-center gap-2 text-xl font-bold">
          <Terminal className="size-5 text-primary" />
          {t("conn_title")}
        </h1>
      </div>
      <div
        className="flex flex-wrap gap-1"
        role="group"
        aria-label={t("th_protocol")}
      >
        <Button
          size="sm"
          variant={!proto ? "secondary" : "ghost"}
          aria-pressed={!proto}
          onClick={() => {
            setProto("");
            setOffset(0);
            setSelected([]);
          }}
        >
          {t("filter_all_protos")}
        </Button>
        {(["tcp", "udp", "icmp"] as const).map((value) => (
          <Button
            key={value}
            size="sm"
            variant={proto === value ? "secondary" : "ghost"}
            aria-pressed={proto === value}
            onClick={() => {
              setProto(value);
              setOffset(0);
              setSelected([]);
            }}
          >
            {t(`proto_${value}`)}
          </Button>
        ))}
      </div>
      <DataState
        pageLoading
        loading={loading && !data}
        error={error}
        hasData={!!data}
        retry={() => {
          void refresh();
        }}
      />
      <OperationNotice notice={notice} close={() => setNotice(null)} />
      {data && (
        <Card>
          <CardHeader>
            <CardTitle>{t("conn_history_title")}</CardTitle>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" disabled={loading || analyzing || !data.items.length} onClick={() => setSelected(selected.length === data.items.length ? [] : data.items.map(item => item.id))}>{t(selected.length === data.items.length && selected.length ? "clear_selection" : "select_page")}</Button>
              <Button size="sm" disabled={loading || analyzing || !selected.length} onClick={() => { void analyze(); }}>{analyzing ? <LoadingOrb state="solving" size={20} text={t("btn_analyzing")} /> : t("analyze_selection", { count: selected.length })}</Button>
            </div>
          </CardHeader>
          <CardContent>
            <PaginatedTable hasRows={data.items.length > 0} emptyMessage={t("no_connections")} dataLoading={loading}
              tableClassName="min-w-[68rem] [&_th]:px-3 [&_td]:px-3"
              offset={data.offset} limit={data.limit} total={data.total} loading={loading || analyzing}
              onChange={(value) => { setOffset(value); setSelected([]); }}
              onLimitChange={(value) => { setPageSize(value); setOffset(0); setSelected([]); }}>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("selection")}</TableHead>
                    <TableHead>{t("th_uid")}</TableHead>
                    <TableHead>{t("th_protocol")}</TableHead>
                    <TableHead>{t("th_source")}</TableHead>
                    <TableHead>{t("th_destination")}</TableHead>
                    <TableHead>{t("th_service")}</TableHead>
                    <TableHead>{t("th_conn_state")}</TableHead>
                    <TableHead>{t("th_duration")}</TableHead>
                    <TableHead>{t("th_bytes")}</TableHead>
                    <TableHead>{t("th_packets")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((conn) => (
                    <TableRow key={conn.id}>
                      <TableCell><Button size="sm" variant={selected.includes(conn.id) ? "secondary" : "ghost"} aria-pressed={selected.includes(conn.id)} aria-label={t("select_connection", { uid: conn.uid })} disabled={analyzing || loading} onClick={() => setSelected(values => values.includes(conn.id) ? values.filter(value => value !== conn.id) : [...values, conn.id])}>{t(selected.includes(conn.id) ? "selected" : "select")}</Button></TableCell>
                      <TableCell className="font-mono text-xs">
                        {conn.uid}
                      </TableCell>
                      <TableCell className="uppercase text-primary">
                        {conn.proto}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {conn.src_ip}:{conn.src_port}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {conn.dst_ip}:{conn.dst_port}
                      </TableCell>
                      <TableCell>{conn.service ?? "—"}</TableCell>
                      <TableCell>{stateBadge(conn.conn_state)}</TableCell>
                      <TableCell>
                        {conn.duration == null ? "—" : conn.duration.toFixed(3)}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {conn.orig_bytes ?? "—"} / {conn.resp_bytes ?? "—"}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {conn.orig_pkts ?? "—"} / {conn.resp_pkts ?? "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
            </PaginatedTable>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
