import { useCallback, useRef, useState } from "react";
import { ArrowLeft, FileWarning, RefreshCw } from "lucide-react";
import { Link } from "@/router";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { TableHeader, TableHead, TableBody, TableRow, TableCell } from "@/components/ui/table";
import { PaginatedTable } from "@/components/paginated-table";
import { LoadingOrb } from "@/components/ui/loading-orb";
import { DataState, OperationNotice, type Notice } from "@/components/data-state";
import { useResource } from "@/hooks/use-resource";
import { useSensorSync } from "@/hooks/use-sensor-sync";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";
import { errorKey } from "@/services/errors";
import { issueLabels } from "@/lib/analysis-labels";

export default function ImportProblemsPage() {
  const { t, language } = useI18n();
  const sync = useSensorSync();
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(20);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const lock = useRef(false);
  const load = useCallback((signal: AbortSignal) => api.getImportProblems(offset, limit, signal), [offset, limit]);
  const resource = useResource(load, true, 0, `import_problems:${offset}:${limit}`);
  const retry = async (id: string) => {
    if (lock.current || sync.syncing) return;
    lock.current = true;
    setBusy(id);
    setNotice(null);
    try {
      await api.retryImportProblem(id);
      await sync.analyze();
      setNotice({ key: "import_problem_retried" });
    } catch (error) {
      setNotice({ key: errorKey(error), error: true });
    } finally {
      await resource.refresh();
      lock.current = false;
      setBusy(null);
    }
  };
  const date = (value: string) => new Date(value).toLocaleString(language === "ro" ? "ro-RO" : "en-GB");
  return <div className="space-y-5 [overflow-anchor:none]">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h1 className="flex items-center gap-2 text-xl font-bold"><FileWarning className="size-5 text-primary" />{t("import_problems_history")}</h1>
      <Button asChild variant="outline" size="sm"><Link to="/dashboard"><ArrowLeft className="size-4" />{t("import_problems_back")}</Link></Button>
    </div>
    <p className="max-w-3xl text-sm text-muted-foreground">{t("import_problems_description")}</p>
    <OperationNotice notice={notice} close={() => setNotice(null)} />
    <Card className="min-h-[calc(100dvh-16rem)]"><CardContent className="pt-6">
      <DataState loading={resource.loading && !resource.data} error={resource.error} hasData={!!resource.data} retry={() => { void resource.refresh(); }} />
      {resource.data && <PaginatedTable {...resource.data} hasRows={!!resource.data.items.length} tableClassName="min-w-[62rem]" emptyMessage={t("import_problems_empty")} loading={resource.loading || sync.syncing || !!busy} dataLoading={resource.loading} onChange={setOffset} onLimitChange={value => { setLimit(value); setOffset(0); }}>
        <TableHeader><TableRow>
          <TableHead>{t("import_problem_file")}</TableHead><TableHead>{t("import_problem_reason")}</TableHead><TableHead>{t("import_problem_first")}</TableHead><TableHead>{t("import_problem_last")}</TableHead><TableHead>{t("import_problem_attempts")}</TableHead><TableHead>{t("th_status")}</TableHead><TableHead>{t("th_action")}</TableHead>
        </TableRow></TableHeader>
        <TableBody>{resource.data.items.map(problem => <TableRow key={problem.id}>
          <TableCell className="max-w-80 break-all font-mono text-xs">{problem.file}</TableCell>
          <TableCell><div className="space-y-1 text-sm"><span>{t(issueLabels[problem.code])}</span>{problem.offset !== null && <p className="text-xs text-muted-foreground">{t("analysis_skip_offset", { offset: problem.offset })}</p>}</div></TableCell>
          <TableCell className="whitespace-nowrap text-xs">{date(problem.first_seen_at)}</TableCell><TableCell className="whitespace-nowrap text-xs">{date(problem.last_seen_at)}</TableCell>
          <TableCell className="tabular-nums">{problem.attempts}</TableCell>
          <TableCell><Badge variant={problem.status === "blocked" ? "destructive" : problem.status === "resolved" ? "success" : problem.status === "retry" ? "default" : "secondary"}>{t(problem.status === "retry" ? "import_problem_retry_queued" : `import_problem_${problem.status}`)}</Badge></TableCell>
          <TableCell><Button variant="outline" size="sm" aria-label={t("import_problem_retry_file", { file: problem.file })} disabled={!!busy || sync.syncing || problem.status !== "blocked"} onClick={() => { void retry(problem.id); }}>
            {busy === problem.id ? <LoadingOrb size={20} text={t("import_problem_retrying")} /> : <><RefreshCw className="size-3.5" />{t("import_problem_retry")}</>}
          </Button></TableCell>
        </TableRow>)}</TableBody>
      </PaginatedTable>}
    </CardContent></Card>
  </div>;
}
