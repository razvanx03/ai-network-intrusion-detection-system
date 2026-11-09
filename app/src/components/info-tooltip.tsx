import { CircleHelp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export function InfoTooltip({ label, text }: { label: string; text: string }) {
  return <TooltipProvider delayDuration={200}><Tooltip>
    <TooltipTrigger asChild><Button variant="ghost" size="icon" className="size-6 shrink-0 text-muted-foreground" aria-label={label}>
      <CircleHelp className="size-3.5" aria-hidden="true" />
    </Button></TooltipTrigger>
    <TooltipContent>{text}</TooltipContent>
  </Tooltip></TooltipProvider>;
}
