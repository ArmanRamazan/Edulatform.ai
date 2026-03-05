interface StreakBadgeProps {
  days: number;
}

const MILESTONES = new Set([7, 30, 100, 365]);

export function StreakBadge({ days }: StreakBadgeProps) {
  const isMilestone = MILESTONES.has(days);

  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold transition-transform ${
        isMilestone
          ? "scale-110 bg-gradient-to-r from-amber-400 to-orange-500 text-white shadow-lg shadow-amber-200"
          : days > 0
            ? "bg-amber-50 text-amber-700 ring-1 ring-amber-200"
            : "bg-gray-100 text-gray-400"
      }`}
    >
      <span
        className={`text-base ${isMilestone ? "animate-bounce" : ""}`}
        role="img"
        aria-label="streak"
      >
        &#x1F525;
      </span>
      <span>
        {days > 0 ? `${days} ${dayWord(days)}` : "Нет серии"}
      </span>
    </div>
  );
}

function dayWord(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return "дней";
  if (mod10 === 1) return "день";
  if (mod10 >= 2 && mod10 <= 4) return "дня";
  return "дней";
}
