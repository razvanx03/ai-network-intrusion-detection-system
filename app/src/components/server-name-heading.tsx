import { InfoTooltip } from "@/components/info-tooltip";
import { useI18n } from "@/i18n";

export function ServerNameHeading() {
  const { t } = useI18n();
  return <span className="inline-flex items-center gap-1">
    {t("context_server_name")}
    <InfoTooltip label={t("context_server_name")} text={t("server_name_help")} />
  </span>;
}
