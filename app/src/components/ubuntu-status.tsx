import { useEffect, useRef, useState } from "react";
import { Monitor, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/services/api";
import type { SensorStatus } from "@/services/types";
import { useI18n, type TranslationKey } from "@/i18n";
import { useSensorSync } from "@/hooks/use-sensor-sync";

const labels: Record<SensorStatus["status"], TranslationKey> = {
  available: "ubuntu_available", unavailable: "ubuntu_unavailable", unauthorized: "ubuntu_unauthorized",
  invalid_response: "ubuntu_invalid", sample_mode: "ubuntu_sample",
  host_unreachable: "ubuntu_host_unreachable", host_unknown: "ubuntu_host_unknown",
};

export function UbuntuStatus() {
  const { analyze, syncing } = useSensorSync();
  const { t, language } = useI18n();
  const [result, setResult] = useState<SensorStatus | null>(null);
  const [checking, setChecking] = useState(true);
  const [failed, setFailed] = useState(false);
  const trigger = useRef<(() => Promise<void>) | null>(null);
  useEffect(() => {
    let active = true;
    let inFlight = false;
    let controller: AbortController | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function check() {
      if (!active || inFlight) return;
      inFlight = true;
      clearTimeout(timer);
      controller = new AbortController();
      setChecking(true);
      try {
        const value = await api.getSensorStatus(controller.signal);
        if (active) {
          setResult(value); setFailed(false);
          if (value.status === "available") {
            // Analysis failures are reported separately by the shared coordinator.
            try { await analyze(true); } catch { /* Keep the reachability result. */ }
          }
        }
      } catch {
        if (active && !controller.signal.aborted) setFailed(true);
      } finally {
        inFlight = false;
        if (active) {
          setChecking(false);
          timer = setTimeout(() => { void check(); }, 60_000);
        }
      }
    }
    trigger.current = check;
    // Synchronize the status indicator with the remote sensor, without overlapping probes.
    // oxlint-disable-next-line react/set-state-in-effect
    void check();
    return () => { active = false; clearTimeout(timer); controller?.abort(); trigger.current = null; };
  }, [analyze]);
  const label = failed ? t("ubuntu_check_failed") : result ? t(labels[result.status]) : t("ubuntu_checking");
  const description = result && !failed ? t("ubuntu_checked_at", { time: new Date(result.checked_at).toLocaleTimeString(language === "ro" ? "ro-RO" : "en-GB") }) : t("ubuntu_probe_help");
  const detail = result?.status === "unavailable" ? t("ubuntu_agent_only_help")
    : result?.status === "host_unreachable" ? t("ubuntu_host_unreachable_help")
    : result?.status === "host_unknown" ? t("ubuntu_host_unknown_help") : t("ubuntu_probe_help");
  return <div className="flex items-center gap-2" title={`${detail} ${description}`}>
    <Monitor className="hidden size-4 text-muted-foreground sm:block" aria-hidden="true" />
    <span className="hidden text-xs font-medium sm:inline">{t("ubuntu_title")}</span>
    <Badge className="w-28 shrink-0 justify-center whitespace-nowrap sm:w-36" variant={failed ? "destructive" : result?.status === "available" ? "success" : result && result.status !== "sample_mode" ? "destructive" : "secondary"} aria-live="polite"><span className="truncate">{label}</span></Badge>
    <Button variant="ghost" size="icon" className="size-8 sm:size-10" disabled={checking || syncing} aria-busy={checking || syncing} aria-label={t("ubuntu_check_now")} onClick={() => { void trigger.current?.(); }}>
      <RefreshCw className={`size-4 ${checking || syncing ? "animate-spin motion-reduce:animate-none" : ""}`} />
    </Button>
  </div>;
}
