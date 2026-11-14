import { forwardRef } from "react";
import { SlidersHorizontal } from "lucide-react";
import { Button, type ButtonProps } from "@/components/ui/button";
import { activeFilterClassName } from "@/lib/filter-controls";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n";

export const FilterButton = forwardRef<HTMLButtonElement, Omit<ButtonProps, "children" | "asChild" | "variant"> & { activeCount: number }>(
  ({ activeCount, disabled, className, ...props }, ref) => {
    const { t } = useI18n();
    const count = disabled ? 0 : activeCount;
    return <Button ref={ref} variant="outline" disabled={disabled} data-active={count > 0}
      aria-label={t(count ? "data_filters_active" : "data_filters", { count })}
      className={cn(count > 0 && activeFilterClassName, className)} {...props}>
      <SlidersHorizontal className="size-4" />{t("data_filters")}
      <span aria-hidden="true" className={cn("inline-flex size-5 items-center justify-center rounded-full bg-primary text-xs font-semibold tabular-nums text-primary-foreground", !count && "invisible")}>{count}</span>
    </Button>;
  },
);
FilterButton.displayName = "FilterButton";
