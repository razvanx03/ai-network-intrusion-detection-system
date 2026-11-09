import { useCallback, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { DataState } from "@/components/data-state";
import { LoadingRegion } from "@/components/loading-region";
import { Pagination } from "@/components/pagination";
import { useResource } from "@/hooks/use-resource";
import { useI18n, type TranslationKey } from "@/i18n";
import { api } from "@/services/api";
import type { Connection, ContextType, ProtocolEvent } from "@/services/types";
import { logKeys } from "@/lib/display";

const fieldLabels: Record<string, TranslationKey> = {
  query: "context_query", qclass_name: "context_qclass", qtype_name: "context_qtype", rcode_name: "context_rcode",
  answers: "context_answers", TTLs: "context_ttl", rejected: "context_rejected", AA: "context_aa", TC: "context_tc",
  RD: "context_rd", RA: "context_ra", trans_id: "context_transaction", rtt: "context_rtt",
  method: "context_method", host: "context_host", uri: "context_uri", version: "context_version",
  user_agent: "context_user_agent", status_code: "context_status", status_msg: "context_status_message",
  request_body_len: "context_request_bytes", response_body_len: "context_response_bytes",
  orig_mime_types: "context_request_mime", resp_mime_types: "context_response_mime", trans_depth: "context_depth",
  server_name: "context_server_name", cipher: "context_cipher", curve: "context_curve", resumed: "context_resumed",
  established: "context_established", next_protocol: "context_next_protocol", validation_status: "context_validation",
  cert_chain_fps: "context_certificates", client_cert_chain_fps: "context_client_certificates",
  subject: "context_subject", issuer: "context_issuer",
};

function ProtocolSection({ connection, kind, includeArchived }: { connection: Connection; kind: ContextType; includeArchived: boolean }) {
  const { t, language } = useI18n();
  const [offset, setOffset] = useState(0);
  const load = useCallback((signal: AbortSignal) => api.getConnectionEvents(connection.id, kind, offset, signal, includeArchived), [connection.id, kind, offset, includeArchived]);
  const cacheKey = `conn_events:${connection.id}:${kind}:${includeArchived}:${offset}`;
  const resource = useResource(load, true, 0, cacheKey);
  const formatValue = (value: ProtocolEvent["fields"][string]): string => {
    if (value === null) return "—";
    if (typeof value === "boolean") return t(value ? "context_yes" : "context_no");
    if (Array.isArray(value)) return value.map(item => formatValue(item)).join(", ") || "—";
    return String(value);
  };
  return <section className="min-w-0 space-y-3 border-t pt-4">
    <h4 className="flex items-center gap-2 text-sm font-semibold">{t(logKeys[kind])} {resource.data && <Badge variant="secondary">{resource.data.total}</Badge>}</h4>
    <DataState loading={false} error={resource.error} hasData={!!resource.data} retry={() => { void resource.refresh(); }} />
    <LoadingRegion loading={resource.loading}>
      {resource.data && (resource.data.items.length ? <ol className="max-h-96 space-y-4 overflow-auto pr-2">
        {resource.data.items.map(event => <li key={event.id} className="space-y-3 rounded-lg bg-muted/30 p-3">
          <time className="text-xs text-muted-foreground" dateTime={new Date(event.ts * 1000).toISOString()}>{new Date(event.ts * 1000).toLocaleString(language === "ro" ? "ro-RO" : "en-GB")}</time>
          <dl className="grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(event.fields).map(([field, value]) => <div key={field} className="min-w-0">
              <dt className="text-xs text-muted-foreground">{t(fieldLabels[field])}</dt>
              <dd className="mt-1 whitespace-pre-wrap break-all text-sm">{formatValue(value)}</dd>
            </div>)}
          </dl>
        </li>)}
      </ol> : <p className="text-sm text-muted-foreground">{t("context_none")}</p>)}
    </LoadingRegion>
    {resource.data && resource.data.total > resource.data.limit && <Pagination {...resource.data} loading={resource.loading} onChange={setOffset} />}
  </section>;
}

export function ConnectionContext({ connection, includeArchived = false }: { connection: Connection; includeArchived?: boolean }) {
  const { t } = useI18n();
  return <div className="min-w-0 space-y-4 py-2">
    <dl>
      <dt className="text-xs text-muted-foreground">{t("context_uid")}</dt>
      <dd className="mt-1 break-all font-mono text-sm">{connection.uid}</dd>
    </dl>
    <dl className="grid gap-3 text-sm sm:grid-cols-3">
      <div><dt className="text-xs text-muted-foreground">{t("context_history")}</dt><dd className="mt-1 break-all font-mono">{connection.history ?? "—"}</dd></div>
      <div><dt className="text-xs text-muted-foreground">{t("th_service")}</dt><dd className="mt-1">{connection.service ?? "—"}</dd></div>
      <div><dt className="text-xs text-muted-foreground">{t("th_duration")}</dt><dd className="mt-1">{connection.duration?.toFixed(3) ?? "—"}</dd></div>
    </dl>
    {(["dns", "http", "ssl"] as const).map(kind => connection.available_logs.includes(kind)
      ? <ProtocolSection key={kind} connection={connection} kind={kind} includeArchived={includeArchived} />
      : <section key={kind} className="flex items-center justify-between border-t pt-3 text-sm"><h4 className="font-semibold">{t(logKeys[kind])}</h4><span className="text-muted-foreground">{t("context_none")}</span></section>)}
  </div>;
}
