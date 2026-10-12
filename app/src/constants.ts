/**
 * Application Constants
 */

// API Configuration - Fail fast if missing, never use silent fallback
const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL;
if (!rawApiBaseUrl) {
  throw new Error(
    "Missing required environment variable: VITE_API_BASE_URL. Please define VITE_API_BASE_URL in your .env configuration."
  );
}
export const API_BASE_URL: string = rawApiBaseUrl;

// Local Storage Keys (Preferences only - Auth is in HttpOnly cookie)
export const STORAGE_KEYS = {
  LANGUAGE: "nids_language",
  THEME: "nids_theme",
} as const;

// Polling & Timing Intervals (ms)
export const TIMING = {
  DASHBOARD_POLL_INTERVAL: 15000,
} as const;

// Security Severity Levels
export const SEVERITIES = {
  CRITICAL: "CRITICAL",
  HIGH: "HIGH",
  MEDIUM: "MEDIUM",
  LOW: "LOW",
} as const;

// Alert Statuses
export const ALERT_STATUSES = {
  NEW: "NEW",
  ACKNOWLEDGED: "ACKNOWLEDGED",
  RESOLVED: "RESOLVED",
  FALSE_POSITIVE: "FALSE_POSITIVE",
} as const;
