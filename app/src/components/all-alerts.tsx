import { useCallback, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TableHeader, TableHead, TableBody, TableRow, TableCell } from "@/components/ui/table";
import { PaginatedTable } from "@/components/paginated-table";
import { DataState } from "@/components/data-state";
import { FindingDetails } from "@/components/dashboard/finding-details";
import { useResource } from "@/hooks/use-resource";
import { useUrlPagination } from "@/hooks/use-url-pagination";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import type { Alert } from "@/services/types";
import { attackKeys } from "@/lib/display";

export function AllAlerts({ refreshVersion }: { refreshVersion: number }) {
  const { t } = useI18n();
  const {
    limit,
    offset,
    setOffset,
    setLimit,
  } = useUrlPagination({
    pageParam: "alert_page",
    limitParam: "alert_limit",
  });
  const [selected, setSelected] = useState<Alert | null>(null);
  const load = useCallback((signal: AbortSignal) => api.getAlerts({ include_archived: true, limit, offset }, signal), [limit, offset]);
  const cacheKey = `alerts:archived:${limit}:${offset}`;
  const resource = useResource(load, true, refreshVersion, cacheKey);
  return <div className="space-y-4"><Card>
    <CardHeader><CardTitle>{t("archive_alerts")}</CardTitle></CardHeader>
    <CardContent>
      <DataState loading={resource.loading && !resource.data} error={resource.error} hasData={!!resource.data} retry={() => { void resource.refresh(); }} />
      {resource.data && <PaginatedTable {...resource.data} hasRows={resource.data.items.length > 0} emptyMessage={t("no_alerts")} loading={resource.loading} dataLoading={resource.loading} onChange={setOffset} onLimitChange={setLimit}>
        <TableHeader><TableRow><TableHead>{t("th_severity")}</TableHead><TableHead>{t("th_attack_type")}</TableHead><TableHead>{t("th_source")}</TableHead><TableHead>{t("th_destination")}</TableHead><TableHead>{t("archive_state")}</TableHead><TableHead>{t("th_action")}</TableHead></TableRow></TableHeader>
        <TableBody>{resource.data.items.map(alert => <TableRow key={alert.id}>
          <TableCell>{t(`severity_${alert.severity}`)}</TableCell>
          <TableCell>{attackKeys[alert.attack_type] ? t(attackKeys[alert.attack_type]) : alert.attack_type}</TableCell>
          <TableCell className="font-mono text-xs">{alert.src_ip}</TableCell><TableCell className="font-mono text-xs">{alert.dst_ip}:{alert.dst_port ?? "—"}</TableCell>
          <TableCell><Badge variant={alert.archive_batch_id ? "secondary" : "success"}>{t(alert.archive_batch_id ? "archive_archived" : "archive_active")}</Badge></TableCell>
          <TableCell><Button variant="outline" size="sm" onClick={() => setSelected(alert)}>{t("finding_details")}</Button></TableCell>
        </TableRow>)}</TableBody>
      </PaginatedTable>}
    </CardContent>
  </Card>{selected && <FindingDetails key={selected.id} alert={selected} includeArchived close={() => setSelected(null)} />}</div>;
}
