import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/i18n";
import type { AlertStatus } from "@/services/types";

const statusColors: Record<AlertStatus, string> = {
  NEW: "border-primary/40 bg-primary/15 text-primary",
  ACKNOWLEDGED: "border-high/50 bg-high/15 text-high",
  RESOLVED: "border-low/50 bg-low/15 text-low",
  FALSE_POSITIVE: "border-violet-500/40 bg-violet-500/15 text-violet-700 dark:text-violet-300",
};

export function AlertStatusBadge({ status }: { status: AlertStatus }) {
  const { t } = useI18n();
  return <Badge variant="outline" className={statusColors[status]}>{t(`status_${status}`)}</Badge>;
}
