import { Card, CardContent } from "@/components/ui/card";
import { useI18n } from "@/i18n";
import type { AlertStats, Overview } from "@/services/types";
import { Database, Flag, Clock } from "lucide-react";
export function Metrics({
  stats,
  overview,
}: {
  stats: AlertStats;
  overview: Overview;
}) {
  const { t, language } = useI18n();
  const cards = [
    {
      label: t("stats_connections"),
      value: overview.connections_total,
      detail: t("stats_connections_sub"),
      surface: "border-primary/35 bg-primary/15 shadow-none",
      accent: "text-primary",
      icon: Database,
    },
    {
      label: t("stats_flagged"),
      value: overview.flagged_connections,
      detail: t("stats_review_pending", { count: stats.unresolved_count }),
      surface: "border-medium/35 bg-medium/15 shadow-none",
      accent: "text-medium",
      icon: Flag,
    },
    {
      label: t("stats_last_sync"),
      value: overview.last_successful_sync ? new Date(overview.last_successful_sync).toLocaleString(language === "ro" ? "ro-RO" : "en-GB") : t("stats_no_sync"),
      valueClass: "text-xl",
      detail: t("stats_last_sync_help"),
      surface: "border-violet-500/35 bg-violet-500/15 shadow-none",
      accent: "text-violet-700 dark:text-violet-300",
      icon: Clock,
    },
  ];
  return (
    <div className="grid grid-cols-1 gap-3.5 md:grid-cols-3">
      {cards.map((card) => (
        <Card key={card.label} className={card.surface}>
          <CardContent className="space-y-2 p-4">
            <div className="flex items-center justify-between gap-2 text-xs font-medium text-foreground">
              <span>{card.label}</span>
              <card.icon className={`size-4 ${card.accent}`} aria-hidden="true" />
            </div>
            <div className={`${card.valueClass ?? "text-3xl"} font-semibold tabular-nums ${card.accent}`}>
              {card.value}
            </div>
            <p className="text-xs text-muted-foreground">{card.detail}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
