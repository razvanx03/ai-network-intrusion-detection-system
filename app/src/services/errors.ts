import type { TranslationKey } from "@/i18n";
import { ApiError } from "./api";
export function errorKey(error: unknown): TranslationKey {
  if (error instanceof ApiError) {
    if (error.code === "import_problem_missing") return "import_problem_missing";
    if (error.code === "import_problem_not_blocked") return "import_problem_not_blocked";
    if (error.code === "reset_not_supported") return "reset_not_supported";
    if (error.code === "reset_sensor_failed") return "reset_sensor_failed";
    if (error.code === "reset_pending") return "reset_resume";
    if (error.code === "archive_empty") return "archive_empty";
    if (error.code === "archive_not_found") return "archive_not_found";
    if (error.code === "archive_snapshot_unavailable") return "archive_snapshot_unavailable";
    if (error.code === "sensor_unavailable") return "analysis_error_sensor";
    if (error.code === "invalid_records") return "analysis_error_records";
    if (error.code === "detector_failed") return "analysis_error_detector";
    if (error.code === "cursor_conflict") return "analysis_error_conflict";
    if (error.code === "processing_failed") return "analysis_error_processing";
    if (error.status === 409) return "analysis_busy";
    if (error.status === 0 || error.status >= 500) return "network_error";
    if (error.status === 401 || error.status === 403) return "session_expired";
  }
  return "operation_error";
}
