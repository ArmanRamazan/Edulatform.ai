import Link from "next/link";
import type { Activity } from "@/lib/api";

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return "только что";
  if (diffMin < 60) {
    return new Intl.RelativeTimeFormat("ru", { numeric: "auto" }).format(-diffMin, "minute");
  }
  if (diffHr < 24) {
    return new Intl.RelativeTimeFormat("ru", { numeric: "auto" }).format(-diffHr, "hour");
  }
  if (diffDay < 7) {
    return new Intl.RelativeTimeFormat("ru", { numeric: "auto" }).format(-diffDay, "day");
  }
  return new Date(dateStr).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
  });
}

function activityDescription(a: Activity): string {
  const name = (a.payload.user_name as string) || "Пользователь";
  switch (a.activity_type) {
    case "quiz_completed":
      return `${name} завершил(а) квиз с результатом ${a.payload.score}%`;
    case "flashcard_reviewed":
      return `${name} повторил(а) ${a.payload.count} флеш-карточек`;
    case "badge_earned":
      return `${name} получил(а) значок \u00AB${a.payload.badge_name}\u00BB`;
    case "streak_milestone":
      return `${name} достиг(ла) серии в ${a.payload.days} дней`;
    case "concept_mastered":
      return `${name} освоил(а) концепт \u00AB${a.payload.concept_name}\u00BB`;
    default:
      return `${name} выполнил(а) действие`;
  }
}

function activityIcon(type: Activity["activity_type"]): string {
  switch (type) {
    case "quiz_completed":
      return "Q";
    case "flashcard_reviewed":
      return "F";
    case "badge_earned":
      return "B";
    case "streak_milestone":
      return "S";
    case "concept_mastered":
      return "C";
    default:
      return "?";
  }
}

const ICON_COLORS: Record<string, string> = {
  quiz_completed: "bg-blue-100 text-blue-700",
  flashcard_reviewed: "bg-green-100 text-green-700",
  badge_earned: "bg-yellow-100 text-yellow-700",
  streak_milestone: "bg-orange-100 text-orange-700",
  concept_mastered: "bg-purple-100 text-purple-700",
};

interface ActivityCardProps {
  activity: Activity;
}

export function ActivityCard({ activity: a }: ActivityCardProps) {
  const name = (a.payload.user_name as string) || "Пользователь";
  const initials = name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const colorClass = ICON_COLORS[a.activity_type] || "bg-gray-100 text-gray-700";

  return (
    <div className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-4">
      <Link
        href={`/users/${a.user_id}`}
        className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gray-200 text-sm font-semibold text-gray-600"
      >
        {initials}
      </Link>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className={`inline-flex h-5 w-5 items-center justify-center rounded text-xs font-bold ${colorClass}`}>
            {activityIcon(a.activity_type)}
          </span>
          <p className="text-sm text-gray-900">{activityDescription(a)}</p>
        </div>
        <p className="mt-1 text-xs text-gray-500">{formatRelativeTime(a.created_at)}</p>
      </div>
    </div>
  );
}
