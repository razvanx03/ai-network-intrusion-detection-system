import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { AlertStatusBadge } from "@/components/alert-status-badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { PaginatedTable } from "@/components/paginated-table";
import { useI18n } from "@/i18n";
import type { Alert, Page, AlertStatus } from "@/services/types";
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuRadioGroup, DropdownMenuRadioItem } from "@/components/ui/dropdown-menu";
export function Alerts({
  page,
  onPage,
  onPageSize,
  updateStatus,
  inspect,
  selectedIds,
  onSelectionChange,
  updateSelectedStatus,
  busy,
  loading,
}: {
  page: Page<Alert>;
  onPage: (offset: number) => void;
  onPageSize: (limit: number) => void;
  updateStatus: (id: number, status: AlertStatus) => void;
  inspect: (alert: Alert) => void;
  selectedIds: number[];
  onSelectionChange: (ids: number[]) => void;
  updateSelectedStatus: (status: AlertStatus) => void;
  busy: boolean;
  loading: boolean;
}) {
  const { t } = useI18n();
  const allSelected = page.items.length > 0 && page.items.every(alert => selectedIds.includes(alert.id));
  const toggle = (id: number, checked: boolean) => onSelectionChange(checked ? [...selectedIds, id] : selectedIds.filter(value => value !== id));
  return (
    <Card>
      <CardHeader className="gap-3">
        <CardTitle>{t("feed_title")}</CardTitle>
        <div className="flex min-h-9 flex-wrap items-center gap-2">
          <span className="min-w-28 text-sm tabular-nums">{t("findings_selected", { count: selectedIds.length })}</span>
          <DropdownMenu modal={false}><DropdownMenuTrigger asChild>
            <Button size="sm" variant="outline" disabled={busy || !selectedIds.length}>{t("findings_bulk_status")}</Button>
          </DropdownMenuTrigger><DropdownMenuContent align="start">
            <DropdownMenuRadioGroup value="" onValueChange={value => updateSelectedStatus(value as AlertStatus)}>
              {(["NEW", "ACKNOWLEDGED", "RESOLVED", "FALSE_POSITIVE"] as const).map(status => <DropdownMenuRadioItem key={status} value={status}>{t(`status_${status}`)}</DropdownMenuRadioItem>)}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent></DropdownMenu>
          <Button size="sm" variant="ghost" disabled={busy || !selectedIds.length} onClick={() => onSelectionChange([])}>{t("clear_selection")}</Button>
        </div>
      </CardHeader>
      <CardContent>
        <PaginatedTable hasRows={page.items.length > 0} emptyMessage={t("no_alerts")} dataLoading={loading}
          offset={page.offset} limit={page.limit} total={page.total} loading={busy}
          onChange={onPage} onLimitChange={onPageSize}>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12"><Checkbox aria-label={t("findings_select_page")} disabled={busy || !page.items.length}
                  checked={allSelected ? true : selectedIds.length ? "indeterminate" : false}
                  onCheckedChange={checked => onSelectionChange(checked ? page.items.map(alert => alert.id) : [])} /></TableHead>
                <TableHead>{t("th_source")}</TableHead>
                <TableHead>{t("th_destination")}</TableHead>
                <TableHead>{t("th_protocol")}</TableHead>
                <TableHead>{t("model_score")}</TableHead>
                <TableHead>{t("th_status")}</TableHead>
                <TableHead>{t("th_action")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {page.items.map((alert) => (
                <TableRow key={alert.id}>
                  <TableCell><Checkbox aria-label={t("findings_select", { id: alert.id })} checked={selectedIds.includes(alert.id)} disabled={busy}
                    onCheckedChange={checked => toggle(alert.id, checked === true)} /></TableCell>
                  <TableCell className="font-mono text-xs">
                    {alert.src_ip}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {alert.dst_ip}
                    {alert.dst_port != null && `:${alert.dst_port}`}
                  </TableCell>
                  <TableCell>{alert.proto?.toUpperCase() ?? "—"}</TableCell>
                  <TableCell className="tabular-nums" title={t("model_score_help")}>{alert.confidence.toFixed(3)}</TableCell>
                  <TableCell>
                    <AlertStatusBadge status={alert.status} />
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button size="sm" variant="outline" onClick={() => inspect(alert)} aria-label={t("finding_inspect", { id: alert.id })}>{t("finding_details")}</Button>
                      <DropdownMenu modal={false}><DropdownMenuTrigger asChild><Button size="sm" variant="ghost" disabled={busy} aria-label={t("finding_change_status", { id: alert.id })}>{t("th_status")}</Button></DropdownMenuTrigger>
                        <DropdownMenuContent align="end"><DropdownMenuRadioGroup value={alert.status} onValueChange={value => updateStatus(alert.id, value as AlertStatus)}>
                          {(["NEW", "ACKNOWLEDGED", "RESOLVED", "FALSE_POSITIVE"] as const).map(status => <DropdownMenuRadioItem key={status} value={status}>{t(`status_${status}`)}</DropdownMenuRadioItem>)}
                        </DropdownMenuRadioGroup></DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
        </PaginatedTable>
      </CardContent>
    </Card>
  );
}
