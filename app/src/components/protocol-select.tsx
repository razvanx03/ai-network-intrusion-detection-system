import { useCallback } from "react";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { DataState } from "@/components/data-state";
import { useResource } from "@/hooks/use-resource";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import { activeFilterClassName } from "@/lib/filter-controls";
import { cn } from "@/lib/utils";

export function ProtocolSelect({ selected, onChange, includeArchived = false, disabled = false, archiveBatchId }: {
  selected: string[]; onChange: (protocols: string[]) => void; includeArchived?: boolean; disabled?: boolean; archiveBatchId?: string;
}) {
  const { t } = useI18n();
  const load = useCallback((signal: AbortSignal) => archiveBatchId ? api.getArchiveProtocols(archiveBatchId, signal) : api.getProtocols(includeArchived, signal), [includeArchived, archiveBatchId]);
  const resource = useResource(load, true, 0, `protocols:${archiveBatchId ?? includeArchived}`);
  const options = [...new Set([...(resource.data ?? []), ...selected])].sort();
  const active = !disabled && selected.length > 0;
  return <DropdownMenu modal={false}>
    <DropdownMenuTrigger asChild><Button variant="outline" disabled={disabled} data-active={active} className={cn("w-52 justify-between", active && activeFilterClassName)} aria-label={t(active ? "protocol_filter_active" : "protocol_filter", { count: selected.length })}>
      <span className="truncate">{selected.length ? selected.map(value => value.toUpperCase()).join(", ") : t("filter_all_protos")}</span><ChevronDown className="size-4 shrink-0" />
    </Button></DropdownMenuTrigger>
    <DropdownMenuContent align="end" className="w-56">
      <DropdownMenuCheckboxItem checked={!selected.length} onSelect={event => event.preventDefault()} onCheckedChange={() => onChange([])}>{t("filter_all_protos")}</DropdownMenuCheckboxItem>
      <DropdownMenuSeparator />
      <DataState loading={resource.loading && !resource.data} error={resource.error} hasData={!!resource.data} retry={() => { void resource.refresh(); }} />
      {options.map(value => <DropdownMenuCheckboxItem key={value} checked={selected.includes(value)} onSelect={event => event.preventDefault()}
        onCheckedChange={checked => onChange(checked ? [...selected, value] : selected.filter(item => item !== value))}>{value.toUpperCase()}</DropdownMenuCheckboxItem>)}
    </DropdownMenuContent>
  </DropdownMenu>;
}
