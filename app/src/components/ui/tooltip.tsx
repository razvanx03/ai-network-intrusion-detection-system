import * as React from "react";
import * as Primitive from "@radix-ui/react-tooltip";
import { cn } from "@/lib/utils";

export const TooltipProvider = Primitive.Provider;
export const Tooltip = Primitive.Root;
export const TooltipTrigger = Primitive.Trigger;
export function TooltipContent({ className, sideOffset = 6, ...props }: React.ComponentProps<typeof Primitive.Content>) {
  return <Primitive.Portal><Primitive.Content sideOffset={sideOffset} className={cn(
    "z-[60] max-w-72 rounded-md border bg-popover px-3 py-2 text-xs font-normal normal-case leading-relaxed tracking-normal text-popover-foreground shadow-md",
    className,
  )} {...props} /></Primitive.Portal>;
}
