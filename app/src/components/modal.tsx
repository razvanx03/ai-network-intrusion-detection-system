import { useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { useI18n } from "@/i18n";

export function Modal({ open, onOpenChange, title, description, children, className }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
}) {
  const { t } = useI18n();
  const descriptionId = useId();
  const opener = useRef<HTMLElement | null>(null);
  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className={className} aria-describedby={description ? descriptionId : undefined}
      onOpenAutoFocus={() => { opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null; }}
      onCloseAutoFocus={event => { event.preventDefault(); if (opener.current?.isConnected) opener.current.focus({ preventScroll: true }); }}>
      <div className="flex shrink-0 items-start justify-between gap-4 border-b px-5 py-4 sm:px-6">
        <div className="min-w-0 space-y-1">
          <DialogTitle className="text-lg font-semibold">{title}</DialogTitle>
          {description && <DialogDescription id={descriptionId} className="text-sm text-muted-foreground">{description}</DialogDescription>}
        </div>
        <DialogClose asChild><Button variant="ghost" size="icon" className="size-8 shrink-0" aria-label={t("close")}><X className="size-4" aria-hidden="true" /></Button></DialogClose>
      </div>
      <div className="min-h-0 overflow-y-auto overscroll-contain p-5 sm:p-6">{children}</div>
    </DialogContent>
  </Dialog>;
}
