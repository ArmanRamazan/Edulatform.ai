"use client";

import Link from "next/link";
import { useAICredits } from "@/hooks/use-ai";

interface AICreditIndicatorProps {
  token: string | null;
}

export function AICreditIndicator({ token }: AICreditIndicatorProps) {
  const { data } = useAICredits(token);

  if (!token || !data) return null;

  const isUnlimited = data.limit === -1 || data.tier === "pro";

  if (isUnlimited) {
    return (
      <span
        className="flex items-center gap-1 rounded bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700"
        title={`${data.used} использовано сегодня`}
      >
        <span className="text-sm">&#x2728;</span>
        Unlimited
      </span>
    );
  }

  const ratio = data.limit > 0 ? data.remaining / data.limit : 0;
  const colorClasses =
    data.remaining === 0
      ? "bg-red-100 text-red-700"
      : ratio > 0.5
        ? "bg-green-100 text-green-700"
        : "bg-yellow-100 text-yellow-700";

  const resetTime = new Date(data.reset_at).toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
  const tooltip = `${data.used}/${data.limit} использовано \u00b7 Сброс в ${resetTime}`;

  const badge = (
    <span
      className={`flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold ${colorClasses}`}
      title={tooltip}
    >
      <span className="text-sm">&#x1F9E0;</span>
      {data.remaining} кр.
    </span>
  );

  if (data.remaining === 0) {
    return <Link href="/pricing">{badge}</Link>;
  }

  return badge;
}
