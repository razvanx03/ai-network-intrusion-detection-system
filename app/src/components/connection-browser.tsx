import { useCallback, useMemo, useState } from "react";
import { ConnectionContext } from "@/components/connection-context";
import { Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { DataState } from "@/components/data-state";
import { Modal } from "@/components/modal";
import { TrafficHeaders, TrafficCells, trafficTableClassName } from "@/components/traffic-columns";
import { ProtocolSelect } from "@/components/protocol-select";
import type { Connection } from "@/services/types";
import { PaginatedTable } from "@/components/paginated-table";
import { useResource } from "@/hooks/use-resource";
import { useUrlPagination } from "@/hooks/use-url-pagination";
import { useSearchParams } from "react-router-dom";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";

export function ConnectionBrowser({ includeArchived = false, refreshVersion = 0, archivedOnly = false, alertsOnly = false, selectedProtocols, hideProtocolFilter = false }: { includeArchived?: boolean; refreshVersion?: number; archivedOnly?: boolean; alertsOnly?: boolean; selectedProtocols?: string[]; hideProtocolFilter?: boolean }) {
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
  const protocols = useMemo(() => selectedProtocols ?? searchParams.getAll(protoParamKey), [selectedProtocols, searchParams, protoParamKey]);
  const setProtocols = (values: string[]) => setSearchParams(previous => {
    const next = new URLSearchParams(previous);
    next.delete(protoParamKey);
    values.forEach(value => next.append(protoParamKey, value));
    next.delete(pageParam);
    return next;
  });

  const [inspected, setInspected] = useState<Connection | null>(null);
  const load = useCallback(
    (signal: AbortSignal) =>
      api.getConnections(
        { protocols, alerts_only: alertsOnly, limit: pageSize, offset, include_archived: includeArchived, archived_only: archivedOnly },
        signal,
      ),
    [protocols, alertsOnly, offset, pageSize, includeArchived, archivedOnly],
  );
  const cacheKey = `connections:${includeArchived ? "archived" : "active"}:${archivedOnly}:${alertsOnly}:${protocols.join(",")}:${pageSize}:${offset}`;
  const { data, loading, error, refresh } = useResource(load, true, refreshVersion, cacheKey);
  return (
    <div className="space-y-6">
      {!includeArchived && <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="flex flex-wrap items-center gap-2 text-xl font-bold">
          <Terminal className="size-5 text-primary" />
          {t("conn_title")}
        </h1>
      </div>}
      {!hideProtocolFilter && <ProtocolSelect selected={protocols} onChange={setProtocols} includeArchived={includeArchived} />}
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
              tableClassName={trafficTableClassName}
              offset={data.offset} limit={data.limit} total={data.total} loading={loading}
              onChange={setOffset}
              onLimitChange={setPageSize}>
                <TableHeader>
                  <TableRow>
                    <TrafficHeaders />
                    <TableHead>{t("th_action")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((conn) => (
                    <TableRow key={conn.id}>
                      <TrafficCells connection={conn} />
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
