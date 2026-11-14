export interface User {
  id: number;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}
export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type AlertStatus =
  "NEW" | "ACKNOWLEDGED" | "RESOLVED" | "FALSE_POSITIVE";
export interface Alert {
  archive_batch_id: string | null;
  id: number;
  timestamp: string;
  connection_id: number | null;
  connection: Connection | null;
  proto: string | null;
  analysis_session_id: string | null;
  provenance: "legacy_demo" | "analysis";
  src_ip: string;
  dst_ip: string;
  dst_port: number | null;
  attack_type: string;
  severity: Severity;
  confidence: number;
  detector: string;
  description: string;
  mitre_technique: string | null;
  status: AlertStatus;
}
export interface Connection {
  archive_batch_id: string | null;
  server_name: string | null;
  available_logs: ("conn" | "dns" | "http" | "ssl")[];
  id: number;
  uid: string;
  ts: number;
  src_ip: string;
  src_port: number;
  dst_ip: string;
  dst_port: number;
  proto: string;
  service: string | null;
  duration: number | null;
  orig_bytes: number | null;
  resp_bytes: number | null;
  conn_state: string | null;
  orig_pkts: number | null;
  resp_pkts: number | null;
  history: string | null;
  created_at: string;
}
export type ContextType = "dns" | "http" | "ssl";
export interface ProtocolEvent {
  id: string;
  uid: string;
  log_type: ContextType;
  ts: number;
  fields: Record<string, string | number | boolean | null | (string | number | boolean | null)[]>;
}
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
export interface AlertStats {
  total_alerts: number;
  unresolved_count: number;
  top_attack_types: { attack_type: string; count: number }[];
}
export interface Overview {
  connections_total: number;
  flagged_connections: number;
  last_successful_sync: string | null;
  running_session_id: string | null;
  protocols: { proto: string; count: number }[];
}
export interface SensorStatus {
  status: "available" | "unavailable" | "host_unreachable" | "host_unknown" | "unauthorized" | "invalid_response" | "sample_mode";
  checked_at: string;
}
export interface Operation {
  status: string;
  message: string;
}
export interface AnalysisResult extends Operation {
  new_connections_ingested: number;
  new_alerts_detected: number;
  alerts_summary: Record<string, number>;
  analysis_session: AnalysisSession;
}
export interface SensorFileIssue {
  file: string;
  code: "corrupt_file" | "unreadable_file" | "oversized_file" | "file_unavailable";
  offset: number | null;
}
export interface SensorFileProblem {
  id: string;
  file: string;
  code: "corrupt_file" | "oversized_file";
  offset: number | null;
  status: "blocked" | "retry" | "resolved" | "outdated";
  attempts: number;
  first_seen_at: string;
  last_seen_at: string;
  first_session_id: string;
  last_session_id: string;
}
export interface AnalysisSession {
  archive_batch_id: string | null;
  id: string;
  source: "sensor" | "stored";
  status: "running" | "completed" | "failed" | "interrupted";
  detector_status: "configured" | "not_configured";
  detector_name: string;
  detector_version: string | null;
  preparation_version: string;
  records_received: number;
  new_connections_ingested: number;
  records_prepared: number;
  new_alerts_detected: number;
  error_code: string | null;
  file_issues: SensorFileIssue[];
  started_at: string;
  finished_at: string | null;
}
export interface AnalysisConnection {
  connection: Connection;
  file_id: string | null;
  file: string | null;
}
export interface ArchiveBatch {
  id: string;
  created_at: string;
  restored_at: string | null;
  connections: number;
  alerts: number;
  sessions: number;
  snapshot_version: number | null;
}

export interface DailyAlerts {
  period_start: string;
  period: "week" | "month";
  today: string;
  timezone: string;
  days: { date: string; count: number }[];
}
