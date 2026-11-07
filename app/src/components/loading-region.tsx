import type { ReactNode } from "react";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { useI18n } from "@/i18n";

/** Preserve content dimensions while replacing only the pending data. */
export function LoadingRegion({ loading, children, contentClassName = "" }: { loading: boolean; children: ReactNode; contentClassName?: string }) {
  const { t } = useI18n();
  return <div className={`relative ${loading && !children ? "min-h-24" : ""}`} aria-busy={loading}>
    <div className={`${loading ? "invisible" : ""} ${contentClassName}`} inert={loading} aria-hidden={loading || undefined}>{children}</div>
    {loading && <div className="absolute inset-0 flex items-center justify-center" role="status">
      <LoadingOrb state="searching" size={20} text={t("loading")} />
    </div>}
  </div>;
}
