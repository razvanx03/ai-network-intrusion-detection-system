import { useContext } from "react";
import { SensorSyncContext } from "@/contexts/sensor-sync-context";

export function useSensorSync() {
  const value = useContext(SensorSyncContext);
  if (!value) throw new Error("useSensorSync requires SensorSyncProvider");
  return value;
}
