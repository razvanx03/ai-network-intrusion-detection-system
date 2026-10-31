import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Pagination } from "@/components/pagination";
import { useI18n } from "@/i18n";
import { attackKeys, descriptionKeys } from "@/lib/display";
import type { Alert, Page, Severity, Provenance, AlertStatus } from "@/services/types";
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuRadioGroup, DropdownMenuRadioItem } from "@/components/ui/dropdown-menu";
const variants = {
  CRITICAL: "critical",
  HIGH: "high",
  MEDIUM: "medium",
  LOW: "low",
} as const;
export function Alerts({
  page,
  severity,
  onFilter,
  onPage,
  updateStatus,
  inspect,
  provenance,
  onProvenance,
  falsePositives,
  busy,
}: {
  page: Page<Alert>;
  severity: Severity | "";
  onFilter: (value: Severity | "") => void;
  onPage: (offset: number) => void;
  updateStatus: (id: number, status: AlertStatus) => void;
  inspect: (alert: Alert) => void;
  provenance: Provenance;
  onProvenance: (value: Provenance) => void;
  falsePositives: number;
  busy: boolean;
}) {
  const { t } = useI18n();
  return (
    <Card>
      <CardHeader className="gap-3">
        <CardTitle>{t("feed_title")}</CardTitle>
        <div className="flex flex-wrap gap-2" role="group" aria-label={t("finding_origin")}>
          {(["analysis", "legacy_demo"] as const).map(value => <Button key={value} size="sm" variant={provenance === value ? "secondary" : "ghost"} aria-pressed={provenance === value} disabled={busy} onClick={() => onProvenance(value)}>{t(value === "analysis" ? "findings_model" : "legacy_demo")}</Button>)}
        </div>
        {provenance === "analysis" && <p className="text-xs text-muted-foreground">{t("findings_false_positive_count", { count: falsePositives })}</p>}
        <div
          className="flex flex-wrap gap-1"
          role="group"
          aria-label={t("th_severity")}
        >
          <Button
            size="sm"
            variant={severity === "" ? "secondary" : "ghost"}
            disabled={busy}
            aria-pressed={severity === ""}
            onClick={() => onFilter("")}
          >
            {t("filter_all_severities")}
          </Button>
          {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((value) => (
            <Button
              key={value}
              size="sm"
              variant={severity === value ? "secondary" : "ghost"}
              disabled={busy}
              aria-pressed={severity === value}
              onClick={() => onFilter(value)}
            >
              {t(`severity_${value}`)}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {!page.items.length ? (
          <p className="py-10 text-center text-sm text-muted-foreground">
            {t("no_alerts")}
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("th_severity")}</TableHead>
                <TableHead>{t("th_attack_type")}</TableHead>
                <TableHead>{t("th_source")}</TableHead>
                <TableHead>{t("th_destination")}</TableHead>
                <TableHead>{t("th_detector")}</TableHead>
                <TableHead>{t("model_score")}</TableHead>
                <TableHead>{t("th_status")}</TableHead>
                <TableHead>{t("th_action")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {page.items.map((alert) => (
                <TableRow key={alert.id}>
                  <TableCell>
                    <Badge variant={variants[alert.severity]}>
                      {t(`severity_${alert.severity}`)}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-medium">
                    {attackKeys[alert.attack_type]
                      ? t(attackKeys[alert.attack_type])
                      : alert.attack_type}
                    <p
                      className="mt-1 max-w-sm truncate text-xs font-normal text-muted-foreground"
                      title={descriptionKeys[alert.description] ? t(descriptionKeys[alert.description]) : alert.description}
                    >
                      {descriptionKeys[alert.description] ? t(descriptionKeys[alert.description]) : alert.description}
                    </p>
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {alert.src_ip}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {alert.dst_ip}
                    {alert.dst_port != null && `:${alert.dst_port}`}
                  </TableCell>
                  <TableCell className="space-y-1 text-xs">
                    <p>{alert.detector}</p>
                    {alert.provenance === "legacy_demo" && <Badge variant="outline">{t("legacy_demo")}</Badge>}
                    {alert.analysis_session_id && <p className="font-mono" title={alert.analysis_session_id}>{alert.analysis_session_id.slice(0, 8)}</p>}
                  </TableCell>
                  <TableCell className="tabular-nums" title={t("model_score_help")}>{alert.confidence.toFixed(3)}</TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        alert.status === "RESOLVED" ? "secondary" : "default"
                      }
                    >
                      {t(`status_${alert.status}`)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button size="sm" variant="outline" onClick={() => inspect(alert)} aria-label={t("finding_inspect", { id: alert.id })}>{t("finding_details")}</Button>
                      <DropdownMenu><DropdownMenuTrigger asChild><Button size="sm" variant="ghost" disabled={busy} aria-label={t("finding_change_status", { id: alert.id })}>{t("th_status")}</Button></DropdownMenuTrigger>
                        <DropdownMenuContent align="end"><DropdownMenuRadioGroup value={alert.status} onValueChange={value => updateStatus(alert.id, value as AlertStatus)}>
                          {(["NEW", "ACKNOWLEDGED", "RESOLVED", "FALSE_POSITIVE"] as const).map(status => <DropdownMenuRadioItem key={status} value={status}>{t(`status_${status}`)}</DropdownMenuRadioItem>)}
                        </DropdownMenuRadioGroup></DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        <Pagination
          offset={page.offset}
          limit={page.limit}
          total={page.total}
          loading={busy}
          onChange={onPage}
        />
      </CardContent>
    </Card>
  );
}
