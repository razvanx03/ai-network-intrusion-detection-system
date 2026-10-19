import { ShieldAlert, Flame, AlertTriangle, Server } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useI18n } from "@/i18n";
import type { AlertStats } from "@/services/types";
export function Metrics({
  stats,
  connections,
}: {
  stats: AlertStats;
  connections: number;
}) {
  const { t } = useI18n();
  const cards = [
    {
      label: t("stats_total_alerts"),
      value: stats.total_alerts,
      detail: `${stats.unresolved_count} ${t("stats_unresolved")}`,
      icon: ShieldAlert,
      color: "text-primary",
    },
    {
      label: t("stats_critical"),
      value: stats.critical_count,
      detail: t("stats_critical_sub"),
      icon: Flame,
      color: "text-critical",
    },
    {
      label: t("stats_high"),
      value: stats.high_count,
      detail: t("stats_high_sub"),
      icon: AlertTriangle,
      color: "text-high",
    },
    {
      label: t("stats_connections"),
      value: connections,
      detail: t("stats_connections_sub"),
      icon: Server,
      color: "text-low",
    },
  ];
  return (
    <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.label}>
          <CardContent className="space-y-1 p-4">
            <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
              <span>{card.label}</span>
              <card.icon className={`size-4 ${card.color}`} />
            </div>
            <div className={`text-2xl font-bold tabular-nums ${card.color}`}>
              {card.value}
            </div>
            <p className="text-xs text-muted-foreground">{card.detail}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
