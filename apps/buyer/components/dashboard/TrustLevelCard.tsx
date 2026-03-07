import type { TrustLevel } from "@/lib/api";

interface TrustLevelCardProps {
  trustLevel: TrustLevel;
}

const LEVEL_NAMES: Record<number, string> = {
  0: "Новичок",
  1: "Исследователь",
  2: "Участник",
  3: "Мастер",
  4: "Эксперт",
  5: "Наставник",
};

const MISSIONS_PER_LEVEL = 10;

export function TrustLevelCard({ trustLevel }: TrustLevelCardProps) {
  const levelName = LEVEL_NAMES[trustLevel.level] ?? `Уровень ${trustLevel.level}`;
  const progressInLevel = trustLevel.total_missions_completed % MISSIONS_PER_LEVEL;
  const progressPct = (progressInLevel / MISSIONS_PER_LEVEL) * 100;

  return (
    <div className="relative overflow-hidden rounded-2xl border border-border bg-card p-5">
      {/* Violet ambient glow — brand moment */}
      <div className="pointer-events-none absolute -right-8 -top-8 h-28 w-28 rounded-full bg-primary/10 blur-2xl" />
      <div className="pointer-events-none absolute -bottom-6 -left-6 h-20 w-20 rounded-full bg-primary/5 blur-xl" />

      <div className="relative">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Уровень доверия
          </span>
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-warning text-sm font-bold text-background">
            {trustLevel.level}
          </span>
        </div>

        <h3 className="mb-4 text-xl font-bold tracking-tight text-foreground">{levelName}</h3>

        {/* Progress bar */}
        <div className="mb-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{progressInLevel}/{MISSIONS_PER_LEVEL} миссий</span>
            <span className="tabular-nums">{Math.round(progressPct)}%</span>
          </div>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-secondary">
            <div
              className="h-full rounded-full bg-gradient-to-r from-warning/80 to-warning transition-all duration-700 ease-out"
              style={{ width: `${progressPct}%` }}
              role="progressbar"
              aria-valuenow={progressInLevel}
              aria-valuemin={0}
              aria-valuemax={MISSIONS_PER_LEVEL}
              aria-label={`${Math.round(progressPct)}% к следующему уровню`}
            />
          </div>
        </div>

        {/* Stats */}
        <div className="mt-4 flex gap-4 text-xs text-muted-foreground">
          <div>
            <span className="block text-lg font-bold tabular-nums text-foreground">
              {trustLevel.total_missions_completed}
            </span>
            миссий
          </div>
          <div>
            <span className="block text-lg font-bold tabular-nums text-foreground">
              {trustLevel.total_concepts_mastered}
            </span>
            концепций
          </div>
        </div>

        {/* Unlocked areas */}
        {trustLevel.unlocked_areas.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {trustLevel.unlocked_areas.map((area) => (
              <span
                key={area}
                className="rounded-full bg-secondary px-2.5 py-0.5 text-xs text-muted-foreground"
              >
                {area}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
