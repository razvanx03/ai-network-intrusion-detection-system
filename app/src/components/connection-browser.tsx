import { useCallback, useState } from "react";
import { ConnectionContext } from "@/components/connection-context";
import { Terminal } from "lucide-react";
import { logKeys } from "@/lib/display";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { DataState } from "@/components/data-state";
import { Modal } from "@/components/modal";
import { InfoTooltip } from "@/components/info-tooltip";
import { PacketsHeading } from "@/components/packets-heading";
import type { Connection } from "@/services/types";
import { PaginatedTable } from "@/components/paginated-table";
import { useResource } from "@/hooks/use-resource";
import { useUrlPagination } from "@/hooks/use-url-pagination";
import { useSearchParams } from "react-router-dom";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";

export function ConnectionBrowser({ includeArchived = false, refreshVersion = 0, archivedOnly = false }: { includeArchived?: boolean; refreshVersion?: number; archivedOnly?: boolean }) {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const pageParam = includeArchived ? "archived_page" : "page";
  const limitParam = includeArchived ? "archived_limit" : "limit";
  const protoParamKey = includeArchived ? "archived_proto" : "proto";
  const {
    limit: pageSize,
    offset,
    setOffset,
    setLimit: setPageSize,
  } = useUrlPagination({
    pageParam,
    limitParam,
  });
  const rawProto = searchParams.get(protoParamKey) || "";
  const proto = (["tcp", "udp", "icmp"].includes(rawProto) ? rawProto : "") as "tcp" | "udp" | "icmp" | "";
  const setProto = (value: string) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (!value) {
        next.delete(protoParamKey);
      } else {
        next.set(protoParamKey, value);
      }
      next.delete(pageParam);
      return next;
    });
  };

  const [inspected, setInspected] = useState<Connection | null>(null);
  const load = useCallback(
    (signal: AbortSignal) =>
      api.getConnections(
        { proto: proto || undefined, limit: pageSize, offset, include_archived: includeArchived, archived_only: archivedOnly },
        signal,
      ),
    [proto, offset, pageSize, includeArchived, archivedOnly],
  );
  const cacheKey = `connections:${includeArchived ? "archived" : "active"}:${archivedOnly}:${proto}:${pageSize}:${offset}`;
  const { data, loading, error, refresh } = useResource(load, true, refreshVersion, cacheKey);
  const stateBadge = (state: string | null) => {
    const label = state === "SF" ? t("state_SF")
      : state === "S0" ? t("state_S0")
      : state === "REJ" ? t("state_REJ") : state ?? "—";
    return <div className="flex min-w-24 items-center gap-1">
      <Badge variant="outline" className="whitespace-nowrap">{state ?? "—"}</Badge>
      {(state === "SF" || state === "S0" || state === "REJ") && <InfoTooltip label={`${t("th_conn_state")}: ${state}`} text={label} />}
    </div>;
  };
  return (
    <div className="space-y-6">
      {!includeArchived && <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="flex flex-wrap items-center gap-2 text-xl font-bold">
          <Terminal className="size-5 text-primary" />
          {t("conn_title")}
        </h1>
      </div>}
      <div
        className="flex flex-wrap gap-1"
        role="group"
        aria-label={t("th_protocol")}
      >
        <Button
          size="sm"
          variant={!proto ? "secondary" : "ghost"}
          aria-pressed={!proto}
          onClick={() => setProto("")}
        >
          {t("filter_all_protos")}
        </Button>
        {(["tcp", "udp", "icmp"] as const).map((value) => (
          <Button
            key={value}
            size="sm"
            variant={proto === value ? "secondary" : "ghost"}
            aria-pressed={proto === value}
            onClick={() => setProto(value)}
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
      {data && (
        <Card>
          <CardContent className="pt-6">
            <PaginatedTable hasRows={data.items.length > 0} emptyMessage={t("no_connections")} dataLoading={loading}
              tableClassName="min-w-[68rem] [&_th]:px-3 [&_td]:px-3"
              offset={data.offset} limit={data.limit} total={data.total} loading={loading}
              onChange={setOffset}
              onLimitChange={setPageSize}>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("context_included")}</TableHead>
                    <TableHead>{t("th_protocol")}</TableHead>
                    <TableHead>{t("th_source")}</TableHead>
                    <TableHead>{t("th_destination")}</TableHead>
                    <TableHead>{t("th_service")}</TableHead>
                    <TableHead>{t("th_conn_state")}</TableHead>
                    <TableHead>{t("th_duration")}</TableHead>
                    <TableHead>{t("th_bytes")}</TableHead>
                    <TableHead><PacketsHeading /></TableHead>
                    <TableHead>{t("th_action")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((conn) => (
                    <TableRow key={conn.id}>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {conn.available_logs.map(kind => <Badge key={kind} variant={kind === "conn" ? "secondary" : "default"} className="px-1.5 text-[10px] uppercase">{t(logKeys[kind])}</Badge>)}
                        </div>
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
                      <TableCell><Button size="sm" variant="outline" aria-label={t("context_inspect", { uid: conn.uid })} onClick={() => setInspected(conn)}>{t("finding_details")}</Button></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
            </PaginatedTable>
          </CardContent>
        </Card>
      )}
      {inspected && <Modal open title={t("context_title")} onOpenChange={open => { if (!open) setInspected(null); }}>
        <ConnectionContext key={inspected.id} connection={inspected} includeArchived={includeArchived} />
      </Modal>}
    </div>
  );
}
