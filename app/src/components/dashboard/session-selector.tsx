import { useId, useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { useI18n } from "@/i18n";
import type { AnalysisSession } from "@/services/types";

export function SessionSelector({ sessions, selectedId, loading, includeArchived, onSelect }: {
  sessions: AnalysisSession[];
  selectedId?: string;
  loading: boolean;
  includeArchived: boolean;
  onSelect: (id: string) => void;
}) {
  const { t, language } = useI18n();
  const [open, setOpen] = useState(false);
  const listId = useId();
  const label = (session: AnalysisSession) => [
    new Date(session.started_at).toLocaleString(language === "ro" ? "ro-RO" : "en-GB"),
    t(`analysis_status_${session.status}`),
    ...(includeArchived ? [t(session.archive_batch_id ? "archive_archived" : "archive_active")] : []),
  ].join(" · ");
  const selected = sessions.find(session => session.id === selectedId);

  return <Popover open={open} onOpenChange={setOpen} modal={false}>
    <PopoverTrigger asChild>
      <Button variant="outline" role="combobox" aria-expanded={open} aria-controls={listId}
        aria-label={t("analysis_select")} disabled={loading} className="w-full justify-between sm:w-[42rem]">
        <span className="truncate">{selected ? label(selected) : t("analysis_select")}</span>
        <ChevronsUpDown className="size-4 shrink-0" aria-hidden="true" />
      </Button>
    </PopoverTrigger>
    <PopoverContent align="start" className="w-[var(--radix-popover-trigger-width)] max-w-[calc(100vw-2rem)] p-0">
      <Command label={t("analysis_sessions")}
        filter={(_value, search, keywords) => (keywords ?? []).join(" ").toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()) ? 1 : 0}>
        <CommandInput placeholder={t("analysis_search")} aria-label={t("analysis_search")} />
        <CommandList id={listId} aria-label={t("analysis_sessions")}>
          <CommandEmpty>{t("analysis_search_empty")}</CommandEmpty>
          {sessions.map(session => <CommandItem key={session.id} value={session.id} keywords={[label(session)]}
            onSelect={() => { onSelect(session.id); setOpen(false); }}>
            <div className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
              <span className="break-words">{label(session)}</span>
              <div className="flex flex-wrap gap-1.5 tabular-nums">
                <Badge variant="outline">{t("analysis_imported")}: {session.new_connections_ingested}</Badge>
                <Badge variant={session.new_alerts_detected > 0 ? "medium" : "outline"}>{t("analysis_findings_count")}: {session.new_alerts_detected}</Badge>
              </div>
            </div>
            <Check className={session.id === selectedId ? "size-4" : "size-4 opacity-0"} aria-hidden="true" />
          </CommandItem>)}
        </CommandList>
      </Command>
    </PopoverContent>
  </Popover>;
}
