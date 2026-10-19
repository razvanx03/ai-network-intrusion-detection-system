import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?:
    | "default"
    | "secondary"
    | "destructive"
    | "outline"
    | "critical"
    | "high"
    | "medium"
    | "low"
    | "success";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variantStyles = {
    default: "bg-primary/20 text-primary border-primary/30",
    secondary: "bg-muted text-foreground border-border",
    destructive: "bg-destructive/10 text-destructive border-destructive/40",
    outline: "border border-border text-foreground",
    critical: "bg-critical/10 text-critical border-critical/60 font-semibold",
    high: "bg-high/10 text-high border-high/60 font-semibold",
    medium: "bg-medium/10 text-medium border-medium/60",
    low: "bg-low/10 text-low border-low/60",
    success: "bg-low/10 text-low border-low/60",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
        variantStyles[variant],
        className,
      )}
      {...props}
    />
  );
}

export { Badge };
