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
  const { theme, t } = useI18n();

  return (
    <span className={cn("inline-flex items-center gap-3", className)}>
      <span aria-hidden="true">
        <ThinkingOrb state={state} size={size} color={color} theme={theme} />
      </span>
      {!text && <span className="sr-only">{t("loading")}</span>}
      {text && <span className="text-sm font-medium text-inherit">{text}</span>}
    </span>
  );
};
