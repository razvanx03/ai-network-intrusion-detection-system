import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { useI18n } from "@/i18n";
import type { AlertStats } from "@/services/types";
const colors = [
  "var(--critical)",
  "var(--high)",
  "var(--medium)",
  "var(--low)",
  "var(--primary)",
];
interface ChartPoint {
  name?: string;
  value?: number;
  color?: string;
  payload?: { fill?: string };
}
function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: readonly ChartPoint[];
}) {
  const { t } = useI18n();
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border bg-popover p-3 text-xs text-popover-foreground shadow-md">
      {payload.map((point, index) => (
        <p key={index}>
          {point.name === "count" ? t("chart_total") : point.name}:{" "}
          {point.value}
        </p>
      ))}
    </div>
  );
}
export default function Charts({ stats, protocols }: { stats: AlertStats; protocols: { proto: string; count: number }[] }) {
  const { t } = useI18n();
  const attacks = protocols.map((item) => ({
    name: item.proto.toUpperCase(),
    value: item.count,
  }));
  const severities = [
    { name: t("severity_CRITICAL"), count: stats.critical_count },
    { name: t("severity_HIGH"), count: stats.high_count },
    { name: t("severity_MEDIUM"), count: stats.medium_count },
    { name: t("severity_LOW"), count: stats.low_count },
  ];
  const ips = stats.top_attacking_ips.map((item) => ({
    name: item.src_ip,
    count: item.count,
  }));
  const empty = (
    <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
      {t("chart_no_data")}
    </div>
  );
  return (
    <div className="grid min-w-0 grid-cols-1 gap-3.5 lg:grid-cols-3">
      <Card className="min-w-0">
        <CardHeader>
          <CardTitle className="text-sm">{t("chart_protocols_title")}</CardTitle>
        </CardHeader>
        <CardContent className="h-64">
          {!attacks.length ? (
            empty
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={attacks}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={42}
                  outerRadius={70}
                  isAnimationActive={false}
                >
                  {attacks.map((item, i) => (
                    <Cell key={item.name} fill={colors[i % colors.length]} />
                  ))}
                </Pie>
                <Tooltip content={<ChartTooltip />} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
      <Card className="min-w-0">
        <CardHeader>
          <CardTitle className="text-sm">{t("chart_severity_title")}</CardTitle>
        </CardHeader>
        <CardContent className="h-64">
          {!stats.total_alerts ? (
            empty
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={severities} margin={{ left: -25, top: 15 }}>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis
                  dataKey="name"
                  stroke="var(--muted-foreground)"
                  fontSize={10}
                />
                <YAxis
                  allowDecimals={false}
                  stroke="var(--muted-foreground)"
                  fontSize={10}
                />
                <Tooltip
                  content={<ChartTooltip />}
                  cursor={{ fill: "var(--muted)" }}
                />
                <Bar
                  dataKey="count"
                  radius={[4, 4, 0, 0]}
                  isAnimationActive={false}
                >
                  {severities.map((item, i) => (
                    <Cell key={item.name} fill={colors[i]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
      <Card className="min-w-0">
        <CardHeader>
          <CardTitle className="text-sm">{t("chart_ip_title")}</CardTitle>
        </CardHeader>
        <CardContent className="h-64">
          {!ips.length ? (
            empty
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ips} layout="vertical" margin={{ top: 15 }}>
                <CartesianGrid stroke="var(--border)" horizontal={false} />
                <XAxis
                  type="number"
                  allowDecimals={false}
                  stroke="var(--muted-foreground)"
                  fontSize={10}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={110}
                  stroke="var(--muted-foreground)"
                  fontSize={10}
                />
                <Tooltip
                  content={<ChartTooltip />}
                  cursor={{ fill: "var(--muted)" }}
                />
                <Bar
                  dataKey="count"
                  fill="var(--low)"
                  radius={[0, 4, 4, 0]}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
