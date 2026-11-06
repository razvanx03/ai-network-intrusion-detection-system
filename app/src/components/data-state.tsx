import { AlertCircle, X } from "lucide-react";
import { useI18n, type TranslationKey } from "@/i18n";
import { errorKey } from "@/services/errors";
import { Button } from "@/components/ui/button";
import { LoadingOrb } from "@/components/ui/loading-orb";

export function DataState({
  loading,
  error, 
  hasData,
  retry,
}: {
  loading: boolean;
  error: unknown;
  hasData: boolean;
  retry: () => void;
}) {
  const { t } = useI18n();
  if (error)
    return (
      <div
        role="alert"
        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm"
      >
        <div>
          <p className="flex items-center gap-2">
            <AlertCircle className="size-4 text-destructive" />
            {t(errorKey(error))}
          </p>
          {hasData && (
            <p className="mt-1 text-muted-foreground">{t("stale_data")}</p>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={retry}>
          {t("retry")}
        </Button>
      </div>
    );
  if (loading)
    return (
      <div role="status">
        <LoadingOrb state="searching" size={20} text={t("loading")} />
      </div>
    );
  return null;
}
export interface Notice {
  key: TranslationKey;
  params?: Record<string, string | number>;
  error?: boolean;
}
export function OperationNotice({
  notice,
  close,
}: {
  notice: Notice | null;
  close: () => void;
}) {
  const { t } = useI18n();
  if (!notice) return null;
  return (
    <div
      role={notice.error ? "alert" : "status"}
      className={`flex items-center justify-between gap-3 rounded-lg border p-3 text-sm ${notice.error ? "border-destructive/40 bg-destructive/10" : "border-low/40 bg-low/10"}`}
    >
      <span>{t(notice.key, notice.params)}</span>
      <Button
        variant="ghost"
        size="icon"
        aria-label={t("close")}
        onClick={close}
      >
        <X className="size-4" />
      </Button>
    </div>
  );
}
