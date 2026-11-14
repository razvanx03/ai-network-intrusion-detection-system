import { ServerNameHeading } from "@/components/server-name-heading";
import { Badge } from "@/components/ui/badge";
import { TableCell, TableHead } from "@/components/ui/table";
import { InfoTooltip } from "@/components/info-tooltip";
import { PacketsHeading } from "@/components/packets-heading";
import { logKeys } from "@/lib/display";
import { useI18n } from "@/i18n";
import type { Alert, Connection } from "@/services/types";

export const trafficTableClassName = "min-w-[84rem] [&_th]:px-2 [&_td]:px-2";

export function TrafficHeaders() {
  const { t } = useI18n();
  return <>
    <TableHead>{t("context_included")}</TableHead><TableHead>{t("th_protocol")}</TableHead>
    <TableHead>{t("th_source")}</TableHead><TableHead>{t("th_destination")}</TableHead>
    <TableHead><ServerNameHeading /></TableHead>
    <TableHead>{t("th_service")}</TableHead><TableHead>{t("th_conn_state")}</TableHead>
    <TableHead>{t("th_duration")}</TableHead><TableHead>{t("th_bytes")}</TableHead>
    <TableHead><PacketsHeading /></TableHead>
  </>;
}

export function TrafficCells({ connection, fallback }: { connection: Connection | null; fallback?: Pick<Alert, "src_ip" | "dst_ip" | "dst_port" | "proto"> }) {
  const { t } = useI18n();
  const state = connection?.conn_state;
  const stateText = state === "SF" ? t("state_SF") : state === "REJ" ? t("state_REJ") : state === "S0" ? t("state_S0") : null;
  return <>
    <TableCell><div className="flex flex-wrap gap-1">
      {connection ? connection.available_logs.map(kind => <Badge key={kind} variant={kind === "conn" ? "secondary" : "default"} className="px-1.5 text-[10px] uppercase">{t(logKeys[kind])}</Badge>) : "—"}
    </div></TableCell>
    <TableCell className="uppercase text-primary">{connection?.proto ?? fallback?.proto ?? "—"}</TableCell>
    <TableCell className="font-mono text-xs">{connection ? `${connection.src_ip}:${connection.src_port}` : fallback?.src_ip ?? "—"}</TableCell>
    <TableCell className="font-mono text-xs">{connection ? `${connection.dst_ip}:${connection.dst_port}` : fallback ? `${fallback.dst_ip}${fallback.dst_port == null ? "" : `:${fallback.dst_port}`}` : "—"}</TableCell>
    <TableCell className="max-w-64 break-all text-xs">{connection?.server_name ?? "—"}</TableCell>
    <TableCell>{connection?.service ?? "—"}</TableCell>
    <TableCell><div className="flex items-center gap-1"><Badge variant="outline">{state ?? "—"}</Badge>
      {stateText && <InfoTooltip label={`${t("th_conn_state")}: ${state}`} text={stateText} />}
    </div></TableCell>
    <TableCell className="tabular-nums">{connection?.duration == null ? "—" : connection.duration.toFixed(3)}</TableCell>
    <TableCell className="font-mono text-xs">{connection?.orig_bytes ?? "—"} / {connection?.resp_bytes ?? "—"}</TableCell>
    <TableCell className="font-mono text-xs">{connection?.orig_pkts ?? "—"} / {connection?.resp_pkts ?? "—"}</TableCell>
  </>;
}
