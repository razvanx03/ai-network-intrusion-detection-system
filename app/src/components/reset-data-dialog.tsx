import { useCallback, useId, useRef, useState } from "react";
import { useNavigate } from "@/router";
import { Modal } from "@/components/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { DataState, OperationNotice, type Notice } from "@/components/data-state";
import { useResource } from "@/hooks/use-resource";
import { useSensorSync } from "@/hooks/use-sensor-sync";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import { errorKey } from "@/services/errors";

export function ResetDataDialog({ close }: { close: () => void }) {
  const { t } = useI18n();
  const sync = useSensorSync();
  const navigate = useNavigate();
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const operationId = useRef(crypto.randomUUID().replaceAll("-", ""));
  const lock = useRef(false);
  const inputId = useId();
  const load = useCallback((signal: AbortSignal) => api.getResetStatus(signal), []);
  const resource = useResource(load);
  const reset = async () => {
    if (lock.current || confirmation !== t("reset_confirmation_token") || !resource.data || sync.syncing) return;
    lock.current = true;
    setBusy(true);
    setNotice(null);
    try {
      await sync.resetData(resource.data.operation_id ?? operationId.current);
      navigate("/dashboard");
      close();
    } catch (error) {
      setNotice({ key: errorKey(error), error: true });
      await resource.refresh();
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  return <Modal open onOpenChange={open => { if (!open && !lock.current) close(); }} title={t("reset_title")} description={t("reset_description")} className="max-w-xl">
    <div className="space-y-5">
      <p className="text-sm font-medium text-destructive">{t("reset_irreversible")}</p>
      <p className="text-sm text-muted-foreground">{t("reset_preserved")}</p>
      <DataState loading={resource.loading} error={resource.error} hasData={!!resource.data} retry={() => { void resource.refresh(); }} />
      {resource.data?.pending && <p className="rounded-lg border p-3 text-sm">{t("reset_resume")}</p>}
      <OperationNotice notice={notice} close={() => setNotice(null)} />
      <div className="space-y-2"><Label htmlFor={inputId}>{t("reset_confirmation_label")}</Label><Input id={inputId} value={confirmation} disabled={busy} autoComplete="off" onChange={event => setConfirmation(event.target.value)} /></div>
      {sync.syncing && !busy && <p className="text-sm text-muted-foreground">{t("analysis_busy")}</p>}
      <div className="flex flex-wrap justify-end gap-2">
        <Button variant="outline" disabled={busy} onClick={close}>{t("cancel")}</Button>
        <Button variant="destructive" disabled={busy || sync.syncing || !resource.data || !!resource.error || confirmation !== t("reset_confirmation_token")} onClick={() => { void reset(); }}>
          {busy ? <LoadingOrb size={20} text={t("reset_working")} /> : t("reset_confirm")}
        </Button>
      </div>
    </div>
  </Modal>;
}
