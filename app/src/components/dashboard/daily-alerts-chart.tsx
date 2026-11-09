import { useCallback, useId, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DataState } from "@/components/data-state";
import { LoadingRegion } from "@/components/loading-region";
import { useResource } from "@/hooks/use-resource";
import { useI18n } from "@/i18n";
import { api } from "@/services/api";

function dateKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
function monday(value: Date) {
  const day = new Date(value);
  day.setDate(day.getDate() - (day.getDay() + 6) % 7);
  return dateKey(day);
}

export function DailyAlertsChart() {
  const { t, language } = useI18n();
  const inputId = useId();
  const [period, setPeriod] = useState<"week" | "month">("week");
  const [anchor, setAnchor] = useState(() => dateKey(new Date()));
  const start = period === "week" ? monday(new Date(`${anchor}T12:00:00`)) : `${anchor.slice(0, 7)}-01`;
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const locale = language === "ro" ? "ro-RO" : "en-GB";
  const load = useCallback((signal: AbortSignal) => api.getDailyAlerts(start, timezone, period, signal), [start, timezone, period]);
  const resource = useResource(load, true, 0, `daily-alerts:${period}:${start}:${timezone}`);
  const today = resource.data?.today;
  const move = (direction: number) => {
    const date = new Date(`${start}T12:00:00`);
    if (period === "month") date.setMonth(date.getMonth() + direction);
    else date.setDate(date.getDate() + direction * 7);
    setAnchor(dateKey(date));
  };
  const days = resource.data?.days.map(day => ({
    ...day,
    label: new Date(`${day.date}T12:00:00`).toLocaleDateString(locale, { weekday: "short", day: "2-digit", month: "2-digit" }).normalize("NFD").replace(/[\u0300-\u036f]/g, ""),
  })) ?? [];

  return <Card className="min-w-0">
    <CardHeader className="space-y-3">
      <CardTitle className="text-sm">{t("chart_daily_title")}</CardTitle>
      <div role="group" aria-label={t("chart_view")} className="flex gap-1">
        {(["week", "month"] as const).map(value => <Button key={value} size="sm"
          variant="outline" className={period === value ? "bg-accent text-accent-foreground" : ""} aria-pressed={period === value}
          onClick={() => setPeriod(value)}>{t(value === "week" ? "chart_view_week" : "chart_view_month")}</Button>)}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Label htmlFor={inputId}>{t(period === "week" ? "chart_week" : "chart_month")}</Label>
        <Input id={inputId} type={period === "week" ? "date" : "month"} value={period === "week" ? start : start.slice(0, 7)}
          min={period === "week" ? "1900-01-01" : "1900-01"} max={period === "week" ? "9998-12-31" : "9998-12"} className="h-9 w-44"
          onChange={event => { if (event.target.value && event.target.validity.valid) setAnchor(period === "week" ? event.target.value : `${event.target.value}-01`); }} />
        <Button variant="outline" size="icon" className="size-9" aria-label={t(period === "week" ? "chart_week_previous" : "chart_month_previous")} onClick={() => move(-1)}><ChevronLeft className="size-4" /></Button>
        <Button variant="outline" size="icon" className="size-9" aria-label={t(period === "week" ? "chart_week_next" : "chart_month_next")} onClick={() => move(1)}><ChevronRight className="size-4" /></Button>
        {period === "week" && <Button variant="ghost" size="sm" onClick={() => setAnchor(dateKey(new Date()))}>{t("chart_week_current")}</Button>}
      </div>
    </CardHeader>
    <CardContent>
      <DataState loading={false} error={resource.error} hasData={!!resource.data} retry={() => { void resource.refresh(); }} />
      <LoadingRegion loading={resource.loading}>
        <div className="h-64" role="img" aria-label={`${t("chart_daily_title")}: ${days.map(day => `${day.date}: ${day.count}`).join(", ")}`}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={days} margin={{ left: -20, right: 8, top: 16, bottom: 12 }}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis dataKey="date" tickFormatter={(value: string) => new Date(`${value}T12:00:00`).toLocaleDateString(locale, { day: "2-digit", month: "2-digit" })}
                stroke="var(--muted-foreground)" fontSize={11} interval={period === "week" ? 0 : "preserveStartEnd"} minTickGap={14} tickMargin={10} />
              <YAxis allowDecimals={false} stroke="var(--muted-foreground)" fontSize={11} domain={[0, (max: number) => Math.max(1, max)]} />
              <Tooltip cursor={{ fill: "var(--muted)" }} content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const day = payload[0].payload as { date: string; label: string; count: number };
                return <div className="rounded-md border bg-popover p-3 text-xs text-popover-foreground shadow-md">
                  <p>{day.label}{day.date === today ? ` · ${t("chart_today")}` : ""}</p>
                  <p className="mt-1 font-semibold">{t("analysis_findings_count")}: {day.count}</p>
                </div>;
              }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false} maxBarSize={56}>
                {days.map(day => <Cell key={day.date} fill={day.date === today ? "var(--primary)" : "var(--medium)"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        {resource.data && <p className="mt-2 text-sm text-muted-foreground">{t(period === "week" ? "chart_week_total" : "chart_month_total", { count: days.reduce((sum, day) => sum + day.count, 0) })}</p>}
      </LoadingRegion>
    </CardContent>
  </Card>;
}
