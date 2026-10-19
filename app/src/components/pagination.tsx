import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n";
export function Pagination({
  offset,
  limit,
  total,
  loading,
  onChange,
}: {
  offset: number;
  limit: number;
  total: number;
  loading: boolean;
  onChange: (offset: number) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
      <span>
        {t("pagination", {
          start: total ? Math.min(offset + 1, total) : 0,
          end: Math.min(offset + limit, total),
          total,
        })}
      </span>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={loading || offset === 0}
          onClick={() => onChange(Math.max(0, offset - limit))}
        >
          {t("previous")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={loading || offset + limit >= total}
          onClick={() => onChange(offset + limit)}
        >
          {t("next")}
        </Button>
      </div>
    </div>
  );
}
