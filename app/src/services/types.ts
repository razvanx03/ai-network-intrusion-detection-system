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
export type Provenance = "analysis" | "legacy_demo";
export interface Alert {
  archive_batch_id: string | null;
  id: number;
  timestamp: string;
  connection_id: number | null;
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
  false_positive_count: number;
  total_alerts: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  unresolved_count: number;
  top_attack_types: { attack_type: string; count: number }[];
  top_attacking_ips: { src_ip: string; count: number }[];
}
export interface Overview {
  connections_total: number;
  flagged_connections: number;
  last_successful_sync: string | null;
  running_session_id: string | null;
  protocols: { proto: string; count: number }[];
}
export interface Health {
  status: string;
  database: string;
  sensor_mode: string;
  connections_total: number;
  alerts_total: number;
  legacy_alerts_total: number;
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
}
