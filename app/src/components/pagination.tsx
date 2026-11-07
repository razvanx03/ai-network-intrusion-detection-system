import { ChevronDown, MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuTrigger,
  DropdownMenuRadioGroup, DropdownMenuRadioItem,
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

export function Pagination({ offset, limit, total, loading, onChange, onLimitChange }: PaginationProps) {
  const { t } = useI18n();
  const pageCount = Math.max(1, Math.ceil(total / limit));
  const currentPage = Math.min(pageCount, Math.floor(offset / limit) + 1);
  const visible = new Set([1, pageCount]);
  const start = pageCount <= 7 ? 1 : currentPage <= 3 ? 2 : currentPage >= pageCount - 2 ? pageCount - 3 : currentPage - 1;
  const end = pageCount <= 7 ? pageCount : currentPage <= 3 ? 4 : currentPage >= pageCount - 2 ? pageCount - 1 : currentPage + 1;
  for (let page = start; page <= end; page++) visible.add(page);
  const pages = [...visible].sort((a, b) => a - b);

  return (
    <nav aria-label={t("pagination_navigation")} className="mt-4 grid grid-cols-1 items-center gap-3 md:grid-cols-[1fr_auto_1fr]">
      <div className="flex flex-wrap items-center justify-center gap-0.5 sm:gap-1 md:col-start-2 md:row-start-1">
        {pages.map((page, index) => <span key={page} className="contents">
          {index > 0 && page - pages[index - 1] > 1 && <span className="flex size-7 items-center justify-center text-muted-foreground sm:size-8">
            <MoreHorizontal className="size-4" aria-hidden="true" /><span className="sr-only">{t("pagination_more")}</span>
          </span>}
          <Button variant={page === currentPage ? "secondary" : "ghost"} size="sm"
            className="min-w-7 px-1 tabular-nums sm:min-w-8 sm:px-2" disabled={loading || total === 0}
            aria-current={page === currentPage ? "page" : undefined}
            aria-label={t("pagination_go_to", { page })}
            onClick={() => onChange((page - 1) * limit)}>{page}</Button>
        </span>)}
      </div>
      {onLimitChange && <div className="flex items-center justify-self-end gap-2 text-sm text-muted-foreground md:col-start-3 md:row-start-1">
        <span>{t("pagination_rows")}</span>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" disabled={loading} aria-label={t("pagination_page_size", { count: limit })}>
              {limit}<ChevronDown className="size-3.5" aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-24">
            <DropdownMenuRadioGroup value={String(limit)} onValueChange={value => onLimitChange(Number(value))}>
              {PAGE_SIZE_OPTIONS.map(size => <DropdownMenuRadioItem key={size} value={String(size)}>{size}</DropdownMenuRadioItem>)}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>}
    </nav>
  );
}
