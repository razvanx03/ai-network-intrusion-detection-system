import { useState, type FormEvent } from "react";
import { ChevronDown, ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from "@/components/ui/dropdown-menu";
import { PAGE_SIZE_OPTIONS } from "@/constants";
import { useI18n } from "@/i18n";

export interface PaginationProps {
  offset: number;
  limit: number;
  total: number;
  loading: boolean;
  onChange: (offset: number) => void;
  onLimitChange?: (limit: number) => void;
}

function EllipsisJump({
  pageCount,
  loading,
  onJump,
}: {
  pageCount: number;
  loading: boolean;
  onJump: (page: number) => void;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const target = parseInt(value, 10);
    if (!isNaN(target)) {
      const clamped = Math.max(1, Math.min(pageCount, target));
      onJump(clamped);
      setValue("");
      setOpen(false);
    }
  };

  return (
    <Popover open={open} onOpenChange={setOpen} modal={false}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="size-7 px-0 text-muted-foreground hover:text-foreground sm:size-8"
          disabled={loading}
          title={t("pagination_jump_title")}
          aria-label={t("pagination_jump_title")}
        >
          <MoreHorizontal className="size-4" aria-hidden="true" />
          <span className="sr-only">{t("pagination_more")}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent align="center" className="w-52 p-3 shadow-lg" aria-label={t("pagination_jump_title")}>
        <div className="mb-2 text-xs font-semibold text-foreground">
          {t("pagination_jump_title")}
        </div>
        <form onSubmit={handleSubmit} className="flex items-center gap-1.5">
          <Input
            type="number"
            min={1}
            max={pageCount}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={`1-${pageCount}`}
            className="h-8 text-center text-xs tabular-nums [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
            autoFocus
            aria-label={t("pagination_jump_label")}
          />
          <Button
            type="submit"
            size="sm"
            className="h-8 px-2.5 text-xs font-normal"
            disabled={loading || !value}
          >
            {t("pagination_jump_button")}
          </Button>
        </form>
        <p className="mt-1.5 text-[11px] text-muted-foreground">
          {t("pagination_of_total", { total: pageCount })}
        </p>
      </PopoverContent>
    </Popover>
  );
}

export function Pagination({
  offset,
  limit,
  total,
  loading,
  onChange,
  onLimitChange,
}: PaginationProps) {
  const { t } = useI18n();
  const [jumpValue, setJumpValue] = useState("");

  const pageCount = Math.max(1, Math.ceil(total / limit));
  const currentPage = Math.min(pageCount, Math.floor(offset / limit) + 1);
  const visible = new Set([1, pageCount]);
  const start =
    pageCount <= 7
      ? 1
      : currentPage <= 3
        ? 2
        : currentPage >= pageCount - 2
          ? pageCount - 3
          : currentPage - 1;
  const end =
    pageCount <= 7
      ? pageCount
      : currentPage <= 3
        ? 4
        : currentPage >= pageCount - 2
          ? pageCount - 1
          : currentPage + 1;
  for (let page = start; page <= end; page++) visible.add(page);
  const pages = [...visible].sort((a, b) => a - b);

  const handleDirectJump = (e: FormEvent) => {
    e.preventDefault();
    const target = parseInt(jumpValue, 10);
    if (!isNaN(target)) {
      const clamped = Math.max(1, Math.min(pageCount, target));
      if (clamped !== currentPage) {
        onChange((clamped - 1) * limit);
      }
      setJumpValue("");
    }
  };

  return (
    <nav
      aria-label={t("pagination_navigation")}
      className="mt-4 grid grid-cols-1 items-center gap-3 md:grid-cols-[1fr_auto_1fr]"
    >
      <div className="flex items-center justify-center md:col-start-1 md:row-start-1 md:justify-start">
        <form
          onSubmit={handleDirectJump}
          className="flex items-center gap-1.5 text-xs text-muted-foreground"
        >
          <span className="whitespace-nowrap font-medium">
            {t("pagination_jump_label")}
          </span>
          <Input
            type="number"
            min={1}
            max={pageCount}
            value={jumpValue}
            onChange={(e) => setJumpValue(e.target.value)}
            placeholder={String(currentPage)}
            disabled={loading || total === 0 || pageCount <= 1}
            className="h-8 w-14 px-1 text-center text-xs tabular-nums [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
            aria-label={t("pagination_jump_label")}
          />
          <span className="whitespace-nowrap text-muted-foreground/80">
            / {pageCount}
          </span>
          <Button
            type="submit"
            variant="outline"
            size="sm"
            className="h-8 px-2 text-xs font-normal"
            disabled={
              loading ||
              total === 0 ||
              pageCount <= 1 ||
              !jumpValue ||
              Number(jumpValue) === currentPage ||
              Number(jumpValue) < 1 ||
              Number(jumpValue) > pageCount
            }
          >
            {t("pagination_jump_button")}
          </Button>
        </form>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-0.5 sm:gap-1 md:col-start-2 md:row-start-1">
        <Button
          variant="ghost"
          size="sm"
          className="size-7 px-0 text-muted-foreground hover:text-foreground sm:size-8"
          disabled={loading || currentPage <= 1}
          aria-label={t("pagination_previous")}
          onClick={() => onChange((currentPage - 2) * limit)}
        >
          <ChevronLeft className="size-4" aria-hidden="true" />
        </Button>
        {pages.map((page, index) => (
          <span key={page} className="contents">
            {index > 0 && page - pages[index - 1] > 1 && (
              <EllipsisJump
                pageCount={pageCount}
                loading={loading}
                onJump={(target) => onChange((target - 1) * limit)}
              />
            )}
            <Button
              variant={page === currentPage ? "secondary" : "ghost"}
              size="sm"
              className="min-w-7 px-1 tabular-nums sm:min-w-8 sm:px-2"
              disabled={loading || total === 0}
              aria-current={page === currentPage ? "page" : undefined}
              aria-label={t("pagination_go_to", { page })}
              onClick={() => onChange((page - 1) * limit)}
            >
              {page}
            </Button>
          </span>
        ))}
        <Button
          variant="ghost"
          size="sm"
          className="size-7 px-0 text-muted-foreground hover:text-foreground sm:size-8"
          disabled={loading || currentPage >= pageCount}
          aria-label={t("pagination_next")}
          onClick={() => onChange(currentPage * limit)}
        >
          <ChevronRight className="size-4" aria-hidden="true" />
        </Button>
      </div>

      {onLimitChange && (
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground md:col-start-3 md:row-start-1 md:justify-end">
          <span>{t("pagination_rows")}</span>
          <DropdownMenu modal={false}>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                disabled={loading}
                aria-label={t("pagination_page_size", { count: limit })}
              >
                {limit}
                <ChevronDown className="size-3.5" aria-hidden="true" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-24">
              <DropdownMenuRadioGroup
                value={String(limit)}
                onValueChange={(value) => onLimitChange(Number(value))}
              >
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <DropdownMenuRadioItem key={size} value={String(size)}>
                    {size}
                  </DropdownMenuRadioItem>
                ))}
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
    </nav>
  );
}
