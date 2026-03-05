import type { Mission } from "@/lib/api";

interface MissionCardProps {
  mission: Mission | null;
  onStart: () => void;
  isStarting: boolean;
}

const STATUS_CONFIG = {
  pending: {
    label: "Ожидает",
    dot: "bg-amber-400",
    bg: "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
  },
  in_progress: {
    label: "В процессе",
    dot: "bg-blue-500 animate-pulse",
    bg: "bg-blue-50 text-blue-700 ring-1 ring-blue-200",
  },
  completed: {
    label: "Завершена",
    dot: "bg-emerald-500",
    bg: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
  },
} as const;

export function MissionCard({ mission, onStart, isStarting }: MissionCardProps) {
  if (!mission) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-gray-200 bg-gray-50/50 p-8 text-center">
        <span className="mb-2 text-3xl" role="img" aria-label="rest">&#x1F3D6;&#xFE0F;</span>
        <p className="text-sm font-medium text-gray-500">На сегодня миссий нет</p>
        <p className="mt-1 text-xs text-gray-400">Отдохните или повторите карточки</p>
      </div>
    );
  }

  const conceptName = mission.blueprint?.concept_name ?? "Миссия";
  const cfg = STATUS_CONFIG[mission.status];

  return (
    <div className="relative overflow-hidden rounded-2xl bg-white p-5 shadow-sm ring-1 ring-gray-100">
      {/* Top accent line */}
      <div className="absolute left-0 right-0 top-0 h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500" />

      <div className="mb-3 flex items-start justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-gray-400">
          Миссия дня
        </span>
        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.bg}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
          {cfg.label}
        </span>
      </div>

      <h3 className="mb-4 text-lg font-bold text-gray-900">{conceptName}</h3>

      {mission.status === "pending" && (
        <button
          onClick={onStart}
          disabled={isStarting}
          className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:from-blue-700 hover:to-indigo-700 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isStarting ? "Запуск..." : "Начать миссию"}
        </button>
      )}

      {mission.status === "in_progress" && (
        <button
          className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:from-blue-700 hover:to-indigo-700 hover:shadow-md"
        >
          Продолжить
        </button>
      )}

      {mission.status === "completed" && mission.score !== null && (
        <div className="flex items-center justify-between rounded-xl bg-emerald-50 px-4 py-3">
          <span className="text-sm text-emerald-600">Результат</span>
          <span className="text-2xl font-bold text-emerald-700">{mission.score}%</span>
        </div>
      )}
    </div>
  );
}
