"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Users, TrendingUp, Activity, CheckCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { useActiveOrg } from "@/hooks/use-active-org";
import { useTeamOverview, type TeamOverviewStats } from "@/hooks/use-analytics";

// ---------- Dark Knowledge chart theme ----------

const CHART_COLORS = [
  "#6b7280", // level 0 — gray
  "#7c5cfc", // level 1 — violet (accent)
  "#818cf8", // level 2 — indigo
  "#34d399", // level 3 — emerald
  "#fbbf24", // level 4 — amber
  "#f97316", // level 5 — orange
];

const TOOLTIP_STYLE = {
  backgroundColor: "#1e1e2e",
  border: "1px solid #3f3f46",
  borderRadius: "8px",
  color: "#e4e4e7",
  fontSize: 12,
};

// ---------- Summary card ----------

interface StatCardProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  sublabel?: string;
}

function StatCard({ icon: Icon, label, value, sublabel }: StatCardProps) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </p>
          <p className="text-2xl font-bold text-card-foreground">{value}</p>
          {sublabel && (
            <p className="text-xs text-muted-foreground">{sublabel}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------- Distribution chart ----------

interface DistributionChartProps {
  distribution: TeamOverviewStats["distribution"];
}

function DistributionChart({ distribution }: DistributionChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Trust Level Distribution
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={distribution}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#3f3f46"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: "#a1a1aa" }}
              axisLine={{ stroke: "#3f3f46" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#a1a1aa" }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              cursor={{ fill: "rgba(124, 92, 252, 0.08)" }}
              formatter={(value: number | undefined) => [value ?? 0, "Members"]}
            />
            <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={48}>
              {distribution.map((entry) => (
                <Cell
                  key={entry.level}
                  fill={CHART_COLORS[entry.level] ?? "#7c5cfc"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// ---------- Loading skeleton ----------

function TeamOverviewSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="flex items-center gap-4 p-4">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <div className="space-y-2">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-7 w-16" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-40" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-60 w-full" />
        </CardContent>
      </Card>
    </div>
  );
}

// ---------- Main component ----------

export function TeamOverview() {
  const { token } = useAuth();
  const { activeOrg } = useActiveOrg();
  const orgId = activeOrg?.id ?? null;

  const { data: stats, isLoading } = useTeamOverview(token, orgId);

  if (isLoading || !stats) {
    return <TeamOverviewSkeleton />;
  }

  return (
    <div className="space-y-6 print:space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Users}
          label="Total Members"
          value={stats.total_members}
        />
        <StatCard
          icon={TrendingUp}
          label="Avg Trust Level"
          value={stats.avg_trust_level}
          sublabel="out of 5"
        />
        <StatCard
          icon={Activity}
          label="Active Today"
          value={stats.active_today}
          sublabel={`${stats.total_members > 0 ? Math.round((stats.active_today / stats.total_members) * 100) : 0}% of team`}
        />
        <StatCard
          icon={CheckCircle}
          label="Completion Rate"
          value={`${stats.completion_rate}%`}
          sublabel="reached Contributor+"
        />
      </div>

      {/* Bar chart */}
      <DistributionChart distribution={stats.distribution} />
    </div>
  );
}
