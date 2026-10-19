import * as React from "react";
import * as Primitive from "@radix-ui/react-dropdown-menu";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
export const DropdownMenu = Primitive.Root;
export const DropdownMenuTrigger = Primitive.Trigger;
export const DropdownMenuRadioGroup = Primitive.RadioGroup;
export function DropdownMenuContent({
  className,
  sideOffset = 4,
  ...props
}: React.ComponentProps<typeof Primitive.Content>) {
  return (
    <Primitive.Portal>
      <Primitive.Content
        sideOffset={sideOffset}
        className={cn(
          "z-50 min-w-48 rounded-md border bg-popover p-1 text-popover-foreground shadow-md",
          className,
        )}
        {...props}
      />
    </Primitive.Portal>
  );
}
export function DropdownMenuLabel({
  className,
  ...props
}: React.ComponentProps<typeof Primitive.Label>) {
  return (
    <Primitive.Label
      className={cn(
        "px-2 py-1.5 text-xs font-semibold text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}
export function DropdownMenuSeparator(
  props: React.ComponentProps<typeof Primitive.Separator>,
) {
  return (
    <Primitive.Separator className="-mx-1 my-1 h-px bg-border" {...props} />
  );
}
export function DropdownMenuRadioItem({
  className,
  children,
  ...props
}: React.ComponentProps<typeof Primitive.RadioItem>) {
  return (
    <Primitive.RadioItem
      className={cn(
        "relative flex cursor-pointer select-none items-center rounded-sm py-2 pl-8 pr-2 text-sm outline-none focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className,
      )}
      {...props}
    >
      <span className="absolute left-2 flex h-4 w-4 items-center justify-center">
        <Primitive.ItemIndicator>
          <Check className="h-4 w-4" />
        </Primitive.ItemIndicator>
      </span>
      {children}
    </Primitive.RadioItem>
  );
}
