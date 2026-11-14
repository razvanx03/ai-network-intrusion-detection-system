import type { TranslationKey } from "@/i18n";
import type { SensorFileIssue } from "@/services/types";

export const issueLabels: Record<SensorFileIssue["code"], TranslationKey> = {
  corrupt_file: "analysis_file_corrupt",
  unreadable_file: "analysis_file_unreadable",
  oversized_file: "analysis_file_oversized",
  file_unavailable: "analysis_file_unavailable",
};

export const errorLabels: Record<string, TranslationKey> = {
  invalid_records: "analysis_error_records",
  sensor_unavailable: "analysis_error_sensor",
  cursor_conflict: "analysis_error_conflict",
  detector_failed: "analysis_error_detector",
  processing_failed: "analysis_error_processing",
  server_restarted: "analysis_error_restart",
  request_interrupted: "analysis_error_interrupted",
};

