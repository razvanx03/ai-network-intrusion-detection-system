import { Card, CardContent } from "@/components/ui/card";
import { useI18n } from "@/i18n";
import type { AlertStats, Overview } from "@/services/types";
import { Database, ShieldCheck, Flag, Layers } from "lucide-react";
export function Metrics({
  stats,
  overview,
}: {
  stats: AlertStats;
  overview: Overview;
}) {
  const { t } = useI18n();
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
      label: t("stats_analyzed"),
      value: overview.analyzed_connections,
      detail: t("stats_pending", { count: overview.pending_connections }),
      surface: "border-low/35 bg-low/15 shadow-none",
      accent: "text-low",
      icon: ShieldCheck,
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
      label: t("stats_sessions"),
      value: overview.sessions_total,
      detail: t("stats_session_breakdown", { completed: overview.completed_sessions, failed: overview.failed_sessions }),
      surface: "border-violet-500/35 bg-violet-500/15 shadow-none",
      accent: "text-violet-700 dark:text-violet-300",
      icon: Layers,
    },
  ];
  return (
    <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.label} className={card.surface}>
          <CardContent className="space-y-2 p-4">
            <div className="flex items-center justify-between gap-2 text-xs font-medium text-foreground">
              <span>{card.label}</span>
              <card.icon className={`size-4 ${card.accent}`} aria-hidden="true" />
            </div>
            <div className={`text-3xl font-semibold tabular-nums ${card.accent}`}>
              {card.value}
            </div>
            <p className="text-xs text-muted-foreground">{card.detail}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
