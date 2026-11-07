import {
  RefreshCw,
  FileSpreadsheet,
  FileCode,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { ArchiveDataButton } from "@/components/archive-data-button";
import { useI18n } from "@/i18n";
export type Command =
  "analyze" | "archive" | "csv" | "json" | "resolve";
export function Commands({
  busy,
  run,
  running = false,
}: {
  busy: Command | null;
  run: (command: Command) => void;
  running?: boolean;
}) {
  const { t } = useI18n();
  return (
    <Card>
      <CardContent className="flex flex-col gap-4 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-base font-semibold">{t("console_title")}</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button className="w-full sm:w-80" onClick={() => run("analyze")} disabled={!!busy || running} aria-busy={busy === "analyze" || running}>
            {busy === "analyze" || running ? (
              <LoadingOrb state="solving" size={20} text={t("btn_fetching_logs")} />
            ) : (
              <>
                <RefreshCw className="size-4" />
                {t("btn_fetch_analyze")}
              </>
            )}
          </Button>
          <ArchiveDataButton busy={busy === "archive"} disabled={!!busy || running} archive={() => run("archive")} />
          <Button variant="ghost" disabled={!!busy} onClick={() => run("csv")}>
            {busy === "csv" ? (
              <LoadingOrb size={20} text={t("btn_exporting")} />
            ) : (
              <>
                <FileSpreadsheet className="size-4" />
                {t("btn_export_csv")}
              </>
            )}
          </Button>
          <Button variant="ghost" disabled={!!busy} onClick={() => run("json")}>
            {busy === "json" ? (
              <LoadingOrb size={20} text={t("btn_exporting")} />
            ) : (
              <>
                <FileCode className="size-4" />
                {t("btn_export_json")}
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
