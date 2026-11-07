import type { ReactNode } from "react";
import { Table } from "@/components/ui/table";
import { Pagination, type PaginationProps } from "@/components/pagination";
import { LoadingRegion } from "@/components/loading-region";

/** Shared table shell; callers supply their typed columns and rows. */
export function PaginatedTable({ children, hasRows, emptyMessage, dataLoading = false, tableClassName, ...pagination }: PaginationProps & {
  children: ReactNode;
  hasRows: boolean;
  emptyMessage: string;
  dataLoading?: boolean;
  tableClassName?: string;
}) {
  return <>
    <LoadingRegion loading={dataLoading}>
      {hasRows ? <Table className={tableClassName}>{children}</Table> : <p className="py-10 text-center text-sm text-muted-foreground">{emptyMessage}</p>}
    </LoadingRegion>
    <Pagination {...pagination} />
  </>;
}
