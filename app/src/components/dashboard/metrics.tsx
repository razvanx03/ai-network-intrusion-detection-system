import { Card, CardContent } from "@/components/ui/card";
import { useI18n } from "@/i18n";
import type { AlertStats, Overview } from "@/services/types";
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
    },
    {
      label: t("stats_analyzed"),
      value: overview.analyzed_connections,
      detail: t("stats_pending", { count: overview.pending_connections }),
    },
    {
      label: t("stats_flagged"),
      value: overview.flagged_connections,
      detail: t("stats_review_pending", { count: stats.unresolved_count }),
    },
    {
      label: t("stats_sessions"),
      value: overview.sessions_total,
      detail: t("stats_session_breakdown", { completed: overview.completed_sessions, failed: overview.failed_sessions }),
    },
  ];
  return (
    <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.label}>
          <CardContent className="space-y-1 p-4">
            <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
              <span>{card.label}</span>
            </div>
            <div className="text-2xl font-semibold tabular-nums">
              {card.value}
            </div>
            <p className="text-xs text-muted-foreground">{card.detail}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
