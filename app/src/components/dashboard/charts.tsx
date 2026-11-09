import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { useI18n } from "@/i18n";
import { DailyAlertsChart } from "@/components/dashboard/daily-alerts-chart";
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
export default function Charts({ protocols }: { protocols: { proto: string; count: number }[] }) {
  const { t } = useI18n();
  const attacks = protocols.map((item) => ({
    name: item.proto.toUpperCase(),
    value: item.count,
  }));
  const empty = (
    <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
      {t("chart_no_data")}
    </div>
  );
  return (
    <div className="grid min-w-0 grid-cols-1 gap-3.5 lg:grid-cols-[1fr_2fr]">
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
      <DailyAlertsChart />
    </div>
  );
}
