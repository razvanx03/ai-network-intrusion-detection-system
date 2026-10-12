import { useEffect, useState, useCallback } from "react";
import { Terminal, RefreshCw, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import { cn } from "@/lib/utils";

export default function ConnectionsPage() {
  const { t } = useI18n();
  const [connections, setConnections] = useState<any[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [protoFilter, setProtoFilter] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const fetchConnections = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.getConnections({ proto: protoFilter || undefined, limit: 100 });
      setConnections(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [protoFilter]);

  useEffect(() => {
    fetchConnections();
  }, [fetchConnections]);

  const getStateBadge = (state: string | null) => {
    if (!state) return <span className="text-slate-600">-</span>;
    if (state === "SF") return <Badge variant="low" className="font-mono text-[10px]">SF (Normal)</Badge>;
    if (state === "S0") return <Badge variant="critical" className="font-mono text-[10px]">S0 (No SYN-ACK)</Badge>;
    if (state === "REJ") return <Badge variant="high" className="font-mono text-[10px]">REJ (Rejected)</Badge>;
    return <Badge variant="outline" className="font-mono text-[10px]">{state}</Badge>;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <Terminal className="w-6 h-6 text-blue-400" />
            {t("conn_title")}
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Modern Protocol Filter Pills Bar */}
          <div className="flex items-center gap-1.5 p-1 bg-slate-950/70 border border-slate-800 rounded-xl shadow-inner">
            <button
              type="button"
              onClick={() => setProtoFilter("")}
              className={cn(
                "px-2.5 py-1 text-xs rounded-lg transition-all duration-150 cursor-pointer select-none",
                protoFilter === ""
                  ? "bg-blue-600 text-white shadow-xs font-semibold"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              )}
            >
              {t("filter_all_protos")}
            </button>
            <button
              type="button"
              onClick={() => setProtoFilter("tcp")}
              className={cn(
                "px-2.5 py-1 text-xs rounded-lg transition-all duration-150 cursor-pointer select-none",
                protoFilter === "tcp"
                  ? "bg-blue-600/30 text-blue-300 border border-blue-500/50 shadow-xs font-semibold"
                  : "text-slate-400 hover:text-blue-300 hover:bg-slate-800/60"
              )}
            >
              TCP
            </button>
            <button
              type="button"
              onClick={() => setProtoFilter("udp")}
              className={cn(
                "px-2.5 py-1 text-xs rounded-lg transition-all duration-150 cursor-pointer select-none",
                protoFilter === "udp"
                  ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 shadow-xs font-semibold"
                  : "text-slate-400 hover:text-cyan-300 hover:bg-slate-800/60"
              )}
            >
              UDP
            </button>
            <button
              type="button"
              onClick={() => setProtoFilter("icmp")}
              className={cn(
                "px-2.5 py-1 text-xs rounded-lg transition-all duration-150 cursor-pointer select-none",
                protoFilter === "icmp"
                  ? "bg-purple-600/30 text-purple-300 border border-purple-500/50 shadow-xs font-semibold"
                  : "text-slate-400 hover:text-purple-300 hover:bg-slate-800/60"
              )}
            >
              ICMP
            </button>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchConnections}
            disabled={isLoading}
            className="gap-2 min-w-[140px] justify-center cursor-pointer border-slate-700 hover:bg-slate-800"
          >
            {isLoading ? (
              <LoadingOrb state="searching" size={20} text={t("btn_refreshing")} />
            ) : (
              <>
                <RefreshCw className="w-3.5 h-3.5" />
                <span>{t("btn_refresh")}</span>
              </>
            )}
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">{t("conn_history_title")}</CardTitle>
              <CardDescription>{t("conn_total")}: {total}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {connections.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm">
              <Layers className="w-8 h-8 mx-auto mb-2 text-slate-600" />
              {t("no_connections")}
            </div>
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
                {connections.map((conn) => (
                  <TableRow key={conn.id}>
                    <TableCell className="font-mono text-xs text-slate-400">{conn.uid}</TableCell>
                    <TableCell>
                      <span className="uppercase text-xs font-semibold text-blue-400">{conn.proto}</span>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-200">
                      {conn.src_ip}:{conn.src_port}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-200">
                      {conn.dst_ip}:{conn.dst_port}
                    </TableCell>
                    <TableCell className="text-xs text-slate-300">
                      {conn.service || <span className="text-slate-600">-</span>}
                    </TableCell>
                    <TableCell>{getStateBadge(conn.conn_state)}</TableCell>
                    <TableCell className="text-xs text-slate-400">
                      {conn.duration ? `${conn.duration.toFixed(3)}s` : "-"}
                    </TableCell>
                    <TableCell className="text-xs font-mono text-slate-300">
                      {conn.orig_bytes || 0} / {conn.resp_bytes || 0}
                    </TableCell>
                    <TableCell className="text-xs font-mono text-slate-400">
                      {conn.orig_pkts || 0} / {conn.resp_pkts || 0}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
