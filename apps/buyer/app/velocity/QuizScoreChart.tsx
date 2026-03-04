"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import type { QuizScoreTrend } from "@/lib/api";

function barColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#eab308";
  return "#ef4444";
}

export default function QuizScoreChart({ data }: { data: QuizScoreTrend[] }) {
  if (data.length === 0) {
    return <p className="flex h-60 items-center justify-center text-sm text-gray-400">Нет данных</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="week" tick={{ fontSize: 12 }} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v) => [`${v}%`, "Средний балл"]} />
        <Bar dataKey="avg_score" radius={[4, 4, 0, 0]} name="Средний балл">
          {data.map((entry, i) => (
            <Cell key={i} fill={barColor(entry.avg_score)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
