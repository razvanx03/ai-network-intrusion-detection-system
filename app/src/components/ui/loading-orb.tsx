import React from "react";
import { ThinkingOrb } from "thinking-orbs";
import type { OrbState, OrbSize } from "thinking-orbs";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/utils";

interface LoadingOrbProps {
  state?: OrbState;
  size?: OrbSize;
  text?: string;
  className?: string;
  color?: string;
}

export const LoadingOrb: React.FC<LoadingOrbProps> = ({
  state = "working",
  size = 32,
  text,
  className,
  color = "#3b82f6",
}) => {
  const { theme } = useI18n();

  return (
    <div className={cn("inline-flex items-center gap-3", className)}>
      <ThinkingOrb state={state} size={size} color={color} theme={theme} />
      {text && (
        <span className="text-sm font-medium text-slate-300 animate-pulse">
          {text}
        </span>
      )}
    </div>
  );
};
