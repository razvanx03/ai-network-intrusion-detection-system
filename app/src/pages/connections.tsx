import { useCallback, useState } from "react";
import { Terminal, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { DataState } from "@/components/data-state";
import { Pagination } from "@/components/pagination";
import { useResource } from "@/hooks/use-resource";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
const PAGE_SIZE = 100;
export default function ConnectionsPage() {
  const { t } = useI18n();
  const [proto, setProto] = useState("");
  const [offset, setOffset] = useState(0);
  const load = useCallback(
    (signal: AbortSignal) =>
      api.getConnections(
        { proto: proto || undefined, limit: PAGE_SIZE, offset },
        signal,
      ),
    [proto, offset],
  );
  const { data, loading, error, refresh } = useResource(load);
  const stateBadge = (state: string | null) => {
    if (state === "SF") return <Badge variant="low">{t("state_SF")}</Badge>;
    if (state === "S0")
      return <Badge variant="critical">{t("state_S0")}</Badge>;
    if (state === "REJ") return <Badge variant="high">{t("state_REJ")}</Badge>;
    return <Badge variant="outline">{state ?? "—"}</Badge>;
  };
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="flex items-center gap-2 text-xl font-bold">
          <Terminal className="size-5 text-primary" />
          {t("conn_title")}
        </h1>
        <Button
          variant="outline"
          disabled={loading}
          onClick={() => {
            void refresh();
          }}
        >
          <RefreshCw className="size-4" />
          {t("btn_refresh")}
        </Button>
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
            }}
          >
            {t(`proto_${value}`)}
          </Button>
        ))}
      </div>
      <DataState
        loading={loading}
        error={error}
        hasData={!!data}
        retry={() => {
          void refresh();
        }}
      />
      {data && (
        <Card>
          <CardHeader>
            <CardTitle>{t("conn_history_title")}</CardTitle>
          </CardHeader>
          <CardContent>
            {!data.items.length ? (
              <p className="py-10 text-center text-sm text-muted-foreground">
                {t("no_connections")}
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
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
              </Table>
            )}
            <Pagination
              offset={data.offset}
              limit={data.limit}
              total={data.total}
              loading={loading}
              onChange={setOffset}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
