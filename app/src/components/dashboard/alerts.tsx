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
import { attackKeys } from "@/lib/display";
import type { Alert, Page, Severity } from "@/services/types";
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
  resolve,
  busy,
}: {
  page: Page<Alert>;
  severity: Severity | "";
  onFilter: (value: Severity | "") => void;
  onPage: (offset: number) => void;
  resolve: (id: number) => void;
  busy: boolean;
}) {
  const { t } = useI18n();
  return (
    <Card>
      <CardHeader className="gap-3">
        <CardTitle>{t("feed_title")}</CardTitle>
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
                <TableHead>{t("th_mitre")}</TableHead>
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
                      title={alert.description}
                    >
                      {alert.description}
                    </p>
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {alert.src_ip}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {alert.dst_ip}
                    {alert.dst_port != null && `:${alert.dst_port}`}
                  </TableCell>
                  <TableCell className="text-xs">{alert.detector}</TableCell>
                  <TableCell>{alert.mitre_technique ?? "—"}</TableCell>
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
                    {alert.status !== "RESOLVED" && (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busy}
                        onClick={() => resolve(alert.id)}
                      >
                        {t("btn_resolve")}
                      </Button>
                    )}
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
