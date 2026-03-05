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
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-800 to-slate-900 p-5 text-white shadow-xl">
      {/* Decorative circles */}
      <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-white/5" />
      <div className="pointer-events-none absolute -bottom-4 -left-4 h-16 w-16 rounded-full bg-white/5" />

      <div className="relative">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Уровень доверия
          </span>
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-500 text-sm font-bold text-slate-900">
            {trustLevel.level}
          </span>
        </div>

        <h3 className="mb-4 text-xl font-bold tracking-tight">{levelName}</h3>

        {/* Progress bar */}
        <div className="mb-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{progressInLevel}/{MISSIONS_PER_LEVEL} миссий</span>
            <span>{Math.round(progressPct)}%</span>
          </div>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-700">
            <div
              className="h-full rounded-full bg-gradient-to-r from-amber-400 to-amber-500 transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {/* Stats */}
        <div className="mt-4 flex gap-4 text-xs text-slate-400">
          <div>
            <span className="block text-lg font-bold text-white">
              {trustLevel.total_missions_completed}
            </span>
            миссий
          </div>
          <div>
            <span className="block text-lg font-bold text-white">
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
                className="rounded-full bg-slate-700 px-2.5 py-0.5 text-xs text-slate-300"
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
