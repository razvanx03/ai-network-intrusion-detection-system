import { useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataState } from "@/components/data-state";
import { useResource } from "@/hooks/use-resource";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import type { Health, Overview } from "@/services/types";

export function SystemStatus({ health, overview }: { health: Health; overview: Overview }) {
  const { t } = useI18n();
  const load = useCallback((signal: AbortSignal) => api.getSensorStatus(signal), []);
  const sensor = useResource(load, 30000);
  const model = overview.detector_name.startsWith("random_forest") ? t("model_random_forest")
    : overview.detector_name.startsWith("logistic_regression") ? t("model_logistic_regression")
      : health.detector_status === "not_configured" ? t("detector_not_configured") : overview.detector_name;
  return <Card><CardContent className="space-y-3 p-4">
    <dl className="grid gap-4 sm:grid-cols-3">
      <div><dt className="text-xs text-muted-foreground">{t("model_active")}</dt><dd className="mt-1 text-sm font-medium">{model}</dd></div>
      <div><dt className="text-xs text-muted-foreground">{t("sensor_connection")}</dt><dd className="mt-1">
        <Badge variant="outline">{sensor.loading ? t("sensor_checking") : sensor.error ? t("sensor_check_failed") : sensor.data ? t(`sensor_status_${sensor.data.status}`) : t("sensor_checking")}</Badge>
      </dd></div>
      <div><dt className="text-xs text-muted-foreground">{t("analysis_execution")}</dt><dd className="mt-1 text-sm">{t(overview.running_session_id ? "analysis_in_progress" : "analysis_manual")}</dd></div>
    </dl>
    <DataState loading={false} error={sensor.error} hasData={!!sensor.data} retry={() => { void sensor.refresh(); }} />
    {!sensor.loading && <Button variant="ghost" size="sm" onClick={() => { void sensor.refresh(); }}>{t("sensor_check_again")}</Button>}
  </CardContent></Card>;
}
