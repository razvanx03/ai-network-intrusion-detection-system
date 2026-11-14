import { createContext } from "react";
import type { AnalysisResult } from "@/services/types";

export const SensorSyncContext = createContext<{
  syncing: boolean;
  revision: number;
  error: unknown;
  dismissError: () => void;
  analyze: (automatic?: boolean) => Promise<AnalysisResult>;
  resetData: (operationId: string) => Promise<void>;
} | null>(null);
