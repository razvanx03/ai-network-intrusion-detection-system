import { LoadingOrb } from "@/components/ui/loading-orb";
import { useI18n } from "@/i18n";

export function PageLoading() {
  const { t } = useI18n();
  return <div role="status" className="flex min-h-80 w-full flex-col items-center justify-center gap-6 py-12 text-center">
    <div className="flex size-16 items-center justify-center" aria-hidden="true">
      <LoadingOrb state="searching" size={64} />
    </div>
    <p className="text-base font-medium tracking-wide text-muted-foreground">{t("page_loading")}</p>
  </div>;
}
