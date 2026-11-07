import type { TranslationKey } from "@/i18n";
import type { Connection } from "@/services/types";
export const logKeys: Record<Connection["available_logs"][number], TranslationKey> = {
  conn: "context_log_conn", dns: "context_log_dns", http: "context_log_http", ssl: "context_log_ssl",
};
export const attackKeys: Record<string, TranslationKey> = {
  "Suspicious Connection": "finding_suspicious_connection",
  "SSH Brute-Force": "attack_ssh",
  "Port Scan": "attack_scan",
  "DoS / SYN Flood": "attack_dos",
  "Statistical Anomaly": "attack_anomaly",
};

export const descriptionKeys: Record<string, TranslationKey> = {
  connection_model_review: "finding_connection_review",
};
