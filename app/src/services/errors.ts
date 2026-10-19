import type { TranslationKey } from "@/i18n";
import { ApiError } from "./api";
export function errorKey(error: unknown): TranslationKey {
  if (error instanceof ApiError) {
    if (error.status === 0 || error.status >= 500) return "network_error";
    if (error.status === 401 || error.status === 403) return "session_expired";
  }
  return "operation_error";
}
