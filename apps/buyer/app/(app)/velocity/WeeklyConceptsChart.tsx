"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface WeeklyConceptsChartProps {
  thisWeek: number;
  lastWeek: number;
}

// Design-system dark palette — matches globals.css CSS variables
const COLORS = {
  bar: "#7c5cfc",       // --primary
  grid: "#1e1e2e",      // --border
  axis: "#6b6b80",      // --muted-foreground
  tooltipBg: "#14141f", // --card
  tooltipBorder: "#1e1e2e",
  tooltipText: "#e2e2e8",
};

export default function WeeklyConceptsChart({ thisWeek, lastWeek }: WeeklyConceptsChartProps) {
  const chartData = [
    { name: "Прош. неделя", value: lastWeek },
    { name: "Эта неделя", value: thisWeek },
  ];

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 12, fill: COLORS.axis }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fontSize: 12, fill: COLORS.axis }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: COLORS.tooltipBg,
            border: `1px solid ${COLORS.tooltipBorder}`,
            borderRadius: "8px",
            fontSize: 12,
            color: COLORS.tooltipText,
          }}
          cursor={{ fill: "rgba(124,92,252,0.06)" }}
        />
        <Bar
          dataKey="value"
          fill={COLORS.bar}
          radius={[4, 4, 0, 0]}
          name="Концепций"
          maxBarSize={56}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
