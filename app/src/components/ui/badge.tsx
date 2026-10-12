import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "critical" | "high" | "medium" | "low" | "success";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variantStyles = {
    default: "bg-blue-600/20 text-blue-400 border-blue-500/30",
    secondary: "bg-slate-800 text-slate-300 border-slate-700",
    destructive: "bg-red-950/50 text-red-400 border-red-800/40",
    outline: "border border-slate-700 text-slate-300",
    critical: "bg-rose-950/60 text-rose-300 border-rose-800/60 font-semibold animate-pulse",
    high: "bg-orange-950/60 text-orange-400 border-orange-800/60 font-semibold",
    medium: "bg-amber-950/60 text-amber-400 border-amber-800/60",
    low: "bg-emerald-950/60 text-emerald-400 border-emerald-800/60",
    success: "bg-emerald-950/60 text-emerald-400 border-emerald-800/60",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
