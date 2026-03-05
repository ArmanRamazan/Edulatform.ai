"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

interface WeeklyConceptsChartProps {
  thisWeek: number;
  lastWeek: number;
}

export default function WeeklyConceptsChart({ thisWeek, lastWeek }: WeeklyConceptsChartProps) {
  const chartData = [
    { name: "Прош. неделя", value: lastWeek },
    { name: "Эта неделя", value: thisWeek },
  ];

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
        <Tooltip />
        <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Концепций" />
      </BarChart>
    </ResponsiveContainer>
  );
}
