interface StreakBadgeProps {
  days: number;
}

const MILESTONES = new Set([7, 30, 100, 365]);

export function StreakBadge({ days }: StreakBadgeProps) {
  const isMilestone = MILESTONES.has(days);

  if (days === 0) {
    return (
      <div className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-sm font-semibold text-muted-foreground">
        <span role="img" aria-label="no streak" className="text-base opacity-40">
          &#x1F525;
        </span>
        Нет серии
      </div>
    );
  }

  if (isMilestone) {
    return (
      <div
        className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-warning to-orange-500 px-3 py-1.5 text-sm font-bold text-white shadow-lg shadow-warning/20 transition-transform hover:scale-105"
        title={`${days}-дневная серия — веха!`}
      >
        <span role="img" aria-label="milestone streak" className="animate-bounce text-base">
          &#x1F525;
        </span>
        {days} {dayWord(days)}
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-1.5 rounded-full bg-warning/10 px-3 py-1.5 text-sm font-semibold text-warning ring-1 ring-warning/20">
      <span role="img" aria-label="active streak" className="text-base">
        &#x1F525;
      </span>
      {days} {dayWord(days)}
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
