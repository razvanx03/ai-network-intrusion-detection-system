import { InfoTooltip } from "@/components/info-tooltip";
import { useI18n } from "@/i18n";

export function PacketsHeading() {
  const { t } = useI18n();
  return <span className="inline-flex items-center gap-1">
    {t("th_packets")}
    <InfoTooltip label={t("packets_help_label")} text={t("packets_help")} />
  </span>;
}
