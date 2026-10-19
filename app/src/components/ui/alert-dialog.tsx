import * as React from "react";
import * as Primitive from "@radix-ui/react-alert-dialog";
import { cn } from "@/lib/utils";
export const AlertDialog = Primitive.Root;
export const AlertDialogTrigger = Primitive.Trigger;
export const AlertDialogAction = Primitive.Action;
export const AlertDialogCancel = Primitive.Cancel;
export function AlertDialogContent({
  className,
  ...props
}: React.ComponentProps<typeof Primitive.Content>) {
  return (
    <Primitive.Portal>
      <Primitive.Overlay className="fixed inset-0 z-50 bg-black/60" />
      <Primitive.Content
        className={cn(
          "fixed left-1/2 top-1/2 z-50 grid w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 rounded-lg border bg-background p-6 shadow-lg",
          className,
        )}
        {...props}
      />
    </Primitive.Portal>
  );
}
export function AlertDialogTitle(
  props: React.ComponentProps<typeof Primitive.Title>,
) {
  return <Primitive.Title className="text-lg font-semibold" {...props} />;
}
export function AlertDialogDescription(
  props: React.ComponentProps<typeof Primitive.Description>,
) {
  return (
    <Primitive.Description
      className="text-sm text-muted-foreground"
      {...props}
    />
  );
}
