import { Archive } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { AlertDialog, AlertDialogTrigger, AlertDialogContent, AlertDialogTitle, AlertDialogDescription, AlertDialogCancel, AlertDialogAction } from "@/components/ui/alert-dialog";
import { useI18n } from "@/i18n";

export function ArchiveDataButton({ busy, disabled, archive }: { busy: boolean; disabled: boolean; archive: () => void }) {
  const { t } = useI18n();
  return <AlertDialog>
    <AlertDialogTrigger asChild><Button variant="outline" disabled={disabled}>
      {busy ? <LoadingOrb size={20} text={t("archive_working")} /> : <><Archive className="size-4" />{t("archive_button")}</>}
    </Button></AlertDialogTrigger>
    <AlertDialogContent>
      <AlertDialogTitle>{t("archive_confirm_title")}</AlertDialogTitle>
      <AlertDialogDescription>{t("archive_confirm_description")}</AlertDialogDescription>
      <div className="flex justify-end gap-2">
        <AlertDialogCancel asChild><Button variant="outline">{t("cancel")}</Button></AlertDialogCancel>
        <AlertDialogAction asChild><Button disabled={disabled} onClick={archive}>{t("archive_button")}</Button></AlertDialogAction>
      </div>
    </AlertDialogContent>
  </AlertDialog>;
}
