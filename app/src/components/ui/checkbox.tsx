import * as React from "react";
import * as Primitive from "@radix-ui/react-checkbox";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export function Checkbox({ className, ...props }: React.ComponentProps<typeof Primitive.Root>) {
  return <Primitive.Root className={cn(
    "peer size-4 shrink-0 rounded-sm border border-primary shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground data-[state=indeterminate]:bg-primary data-[state=indeterminate]:text-primary-foreground",
    className,
  )} {...props}>
    <Primitive.Indicator className="flex items-center justify-center text-current"><Check className="size-3.5" aria-hidden="true" /></Primitive.Indicator>
  </Primitive.Root>;
}
