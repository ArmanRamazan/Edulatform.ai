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
import type { QuizScoreTrend } from "@/lib/api";

// Design-system dark palette — matches globals.css CSS variables
const COLORS = {
  high: "#34d399",      // --success
  mid: "#fbbf24",       // --warning
  low: "#f87171",       // --destructive
  grid: "#1e1e2e",      // --border
  axis: "#6b6b80",      // --muted-foreground
  tooltipBg: "#14141f", // --card
  tooltipBorder: "#1e1e2e",
  tooltipText: "#e2e2e8",
};

function barColor(score: number): string {
  if (score >= 80) return COLORS.high;
  if (score >= 60) return COLORS.mid;
  return COLORS.low;
}

export default function QuizScoreChart({ data }: { data: QuizScoreTrend[] }) {
  if (data.length === 0) {
    return (
      <div className="flex h-60 items-center justify-center">
        <p className="text-sm text-muted-foreground">Нет данных о квизах</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} vertical={false} />
        <XAxis
          dataKey="week"
          tick={{ fontSize: 12, fill: COLORS.axis }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 12, fill: COLORS.axis }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(v) => [`${v}%`, "Средний балл"]}
          contentStyle={{
            background: COLORS.tooltipBg,
            border: `1px solid ${COLORS.tooltipBorder}`,
            borderRadius: "8px",
            fontSize: 12,
            color: COLORS.tooltipText,
          }}
          cursor={{ fill: "rgba(124,92,252,0.06)" }}
        />
        <Bar dataKey="avg_score" radius={[4, 4, 0, 0]} name="Средний балл" maxBarSize={56}>
          {data.map((entry, i) => (
            <Cell key={i} fill={barColor(entry.avg_score)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
