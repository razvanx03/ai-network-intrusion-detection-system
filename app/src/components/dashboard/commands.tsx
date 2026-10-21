import {
  RefreshCw,
  Server,
  Trash2,
  FileSpreadsheet,
  FileCode,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingOrb } from "@/components/ui/loading-orb";
import {
  AlertDialog,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogCancel,
  AlertDialogAction,
} from "@/components/ui/alert-dialog";
import { useI18n } from "@/i18n";
export type Command =
  "analyze" | "sensor" | "clear" | "csv" | "json" | "resolve";
export function Commands({
  busy,
  run,
  detectorStatus,
}: {
  busy: Command | null;
  run: (command: Command) => void;
  detectorStatus?: "configured" | "not_configured";
}) {
  const { t } = useI18n();
  return (
    <Card>
      <CardContent className="flex flex-col gap-4 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-base font-semibold">{t("console_title")}</h1>
          {detectorStatus && <Badge variant="outline">{t(`detector_${detectorStatus}`)}</Badge>}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => run("analyze")} disabled={!!busy}>
            {busy === "analyze" ? (
              <LoadingOrb state="solving" size={20} text={t("btn_analyzing")} />
            ) : (
              <>
                <RefreshCw className="size-4" />
                {t("btn_fetch_analyze")}
              </>
            )}
          </Button>
          <Button
            variant="outline"
            onClick={() => run("sensor")}
            disabled={!!busy}
          >
            {busy === "sensor" ? (
              <LoadingOrb size={20} text={t("btn_resetting_sensor")} />
            ) : (
              <>
                <Server className="size-4" />
                {t("btn_reset_sensor")}
              </>
            )}
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" disabled={!!busy}>
                {busy === "clear" ? (
                  <LoadingOrb size={20} text={t("btn_clearing_db")} />
                ) : (
                  <>
                    <Trash2 className="size-4" />
                    {t("btn_reset_db")}
                  </>
                )}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogTitle>{t("clear_title")}</AlertDialogTitle>
              <AlertDialogDescription>
                {t("confirm_clear_db")}
              </AlertDialogDescription>
              <div className="flex justify-end gap-2">
                <AlertDialogCancel asChild>
                  <Button variant="outline">{t("cancel")}</Button>
                </AlertDialogCancel>
                <AlertDialogAction asChild>
                  <Button
                    variant="destructive"
                    disabled={!!busy}
                    onClick={() => run("clear")}
                  >
                    {t("btn_reset_db")}
                  </Button>
                </AlertDialogAction>
              </div>
            </AlertDialogContent>
          </AlertDialog>
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
