import { motion } from "framer-motion";
import Link from "next/link";
import { Target, Palmtree } from "lucide-react";
import type { Mission } from "@/lib/api";

interface MissionCardProps {
  mission: Mission | null;
  onStart: () => void;
  isStarting: boolean;
}

const STATUS_CONFIG = {
  pending: {
    label: "Ожидает",
    dot: "bg-warning animate-pulse",
    chip: "bg-warning/10 text-warning ring-1 ring-warning/20",
  },
  in_progress: {
    label: "В процессе",
    dot: "bg-info animate-pulse",
    chip: "bg-info/10 text-info ring-1 ring-info/20",
  },
  completed: {
    label: "Завершена",
    dot: "bg-success",
    chip: "bg-success/10 text-success ring-1 ring-success/20",
  },
} as const;

export function MissionCard({ mission, onStart, isStarting }: MissionCardProps) {
  // ── Empty state ──────────────────────────────────────────────────────────
  if (!mission) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-border bg-card/50 p-8 text-center">
        <Palmtree
          className="h-10 w-10 text-muted-foreground/40"
          aria-hidden="true"
          strokeWidth={1.5}
        />
        <div>
          <p className="text-sm font-medium text-muted-foreground">На сегодня миссий нет</p>
          <p className="mt-0.5 text-xs text-muted-foreground/60">
            Отдохните или повторите карточки
          </p>
        </div>
      </div>
    );
  }

  const conceptName = mission.blueprint?.concept_name ?? "Миссия";
  const cfg = STATUS_CONFIG[mission.status];

  return (
    <motion.div
      className="relative overflow-hidden rounded-2xl border border-border bg-card p-5"
      whileHover={{ scale: 1.005 }}
      transition={{ duration: 0.15 }}
    >
      {/* Top accent: violet gradient — Dark Knowledge brand */}
      <div className="absolute left-0 right-0 top-0 h-0.5 bg-gradient-to-r from-primary/60 via-primary to-primary/60" />

      {/* Ambient glow behind the card */}
      <div className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-primary/5 blur-2xl" />

      <div className="relative">
        <div className="mb-3 flex items-start justify-between">
          <span className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <Target className="h-3.5 w-3.5" aria-hidden="true" />
            Миссия дня
          </span>
          <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.chip}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} aria-hidden="true" />
            {cfg.label}
          </span>
        </div>

        <h3 className="mb-4 text-lg font-bold text-foreground">{conceptName}</h3>

        {mission.status === "pending" && (
          <button
            onClick={onStart}
            disabled={isStarting}
            className="w-full rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 hover:shadow-primary/20 hover:shadow-md active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isStarting ? (
              <span className="flex items-center justify-center gap-2">
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground" />
                Запуск...
              </span>
            ) : (
              "Начать миссию"
            )}
          </button>
        )}

        {mission.status === "in_progress" && (
          <Link
            href={`/missions/${mission.id}`}
            className="block w-full rounded-xl bg-info/10 px-4 py-2.5 text-center text-sm font-semibold text-info ring-1 ring-info/20 transition-all hover:bg-info/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Продолжить →
          </Link>
        )}

        {mission.status === "completed" && mission.score !== null && (
          <div className="flex items-center justify-between rounded-xl bg-success/10 px-4 py-3 ring-1 ring-success/20">
            <span className="text-sm text-success/80">Результат</span>
            <span className="text-2xl font-bold tabular-nums text-success">{mission.score}%</span>
          </div>
        )}
      </div>
    </motion.div>
  );
}
