"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Target,
  CheckCircle2,
  Clock,
  Flame,
  AlertCircle,
  RefreshCw,
  Sparkles,
  ChevronRight,
  Swords,
} from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useMissionHistory } from "@/hooks/use-daily";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { Mission } from "@/lib/api";

// ── Status helpers ───────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  Mission["status"],
  { label: string; icon: typeof Target; colorClass: string; badgeVariant: "default" | "secondary" | "outline" }
> = {
  in_progress: {
    label: "В процессе",
    icon: Clock,
    colorClass: "text-warning",
    badgeVariant: "default",
  },
  pending: {
    label: "Ожидает",
    icon: Target,
    colorClass: "text-muted-foreground",
    badgeVariant: "secondary",
  },
  completed: {
    label: "Завершена",
    icon: CheckCircle2,
    colorClass: "text-success",
    badgeVariant: "outline",
  },
};

function missionTypeLabel(type: string): string {
  switch (type) {
    case "daily":
      return "Ежедневная";
    case "concept":
      return "Концепт";
    case "review":
      return "Повторение";
    case "challenge":
      return "Вызов";
    default:
      return type;
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("ru", {
    day: "numeric",
    month: "short",
  });
}

// ── Tab type ─────────────────────────────────────────────────────────────────

type Tab = "active" | "completed";

// ── Skeleton ─────────────────────────────────────────────────────────────────

function MissionsSkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading missions">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="rounded-xl border border-border bg-card p-4"
        >
          <div className="flex items-center gap-4">
            <Skeleton className="h-10 w-10 shrink-0 rounded-lg" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
            <Skeleton className="h-6 w-20 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Mission card ─────────────────────────────────────────────────────────────

function MissionCard({ mission, index }: { mission: Mission; index: number }) {
  const config = STATUS_CONFIG[mission.status];
  const StatusIcon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.05 }}
    >
      <Link
        href={`/missions/${mission.id}`}
        className="group flex items-center gap-4 rounded-xl border border-border bg-card p-4 transition-all hover:border-primary/30 hover:bg-card/80"
      >
        {/* Icon */}
        <div
          className={[
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
            mission.status === "completed"
              ? "bg-success/10"
              : mission.status === "in_progress"
                ? "bg-warning/10"
                : "bg-primary/10",
          ].join(" ")}
        >
          <StatusIcon
            className={`h-5 w-5 ${config.colorClass}`}
            aria-hidden="true"
            strokeWidth={1.5}
          />
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">
            {mission.blueprint?.concept_name ?? `Миссия ${mission.id.slice(0, 8)}`}
          </p>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            <span>{missionTypeLabel(mission.mission_type)}</span>
            {mission.score !== null && (
              <>
                <span className="text-border">|</span>
                <span className="tabular-nums text-primary font-medium">
                  {mission.score} баллов
                </span>
              </>
            )}
            {(mission.completed_at || mission.started_at) && (
              <>
                <span className="text-border">|</span>
                <span>{formatDate(mission.completed_at ?? mission.started_at)}</span>
              </>
            )}
          </div>
        </div>

        {/* Status badge */}
        <Badge variant={config.badgeVariant} className="shrink-0 text-xs">
          {config.label}
        </Badge>

        {/* Chevron */}
        <ChevronRight
          className="h-4 w-4 shrink-0 text-muted-foreground/40 transition-transform group-hover:translate-x-0.5 group-hover:text-primary"
          aria-hidden="true"
        />
      </Link>
    </motion.div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function MissionsPage() {
  const { token, user, loading: authLoading } = useAuth();
  const {
    data: historyData,
    isLoading,
    isError,
    refetch,
  } = useMissionHistory(token, 50);

  const [tab, setTab] = useState<Tab>("active");

  // Split missions into active / completed
  const allMissions = historyData?.items ?? [];
  const activeMissions = allMissions.filter(
    (m) => m.status === "in_progress" || m.status === "pending",
  );
  const completedMissions = allMissions.filter(
    (m) => m.status === "completed",
  );
  const displayedMissions = tab === "active" ? activeMissions : completedMissions;

  // ── Auth loading ──
  if (authLoading) {
    return (
      <div className="mx-auto max-w-3xl">
        <Skeleton className="mb-6 h-7 w-32" />
        <MissionsSkeleton />
      </div>
    );
  }

  // ── Unauthenticated ──
  if (!user || !token) {
    return (
      <div className="mx-auto max-w-3xl">
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-border bg-card py-16 text-center">
          <Swords
            className="h-10 w-10 text-muted-foreground/30"
            strokeWidth={1.5}
            aria-hidden="true"
          />
          <p className="text-sm text-muted-foreground">
            <Link
              href="/login"
              className="text-primary underline underline-offset-2 hover:text-primary/80"
            >
              Войдите
            </Link>
            , чтобы увидеть свои миссии.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-foreground">Миссии</h1>
        {historyData && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Flame className="h-3.5 w-3.5 text-warning" aria-hidden="true" />
            <span className="tabular-nums">{completedMissions.length}</span>
            <span>завершено</span>
          </div>
        )}
      </div>

      {/* Tab switcher */}
      <div className="mb-6 flex gap-1 rounded-xl bg-secondary p-1">
        {(["active", "completed"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={[
              "flex-1 rounded-lg py-2 text-sm font-medium transition-all",
              tab === t
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            {t === "active" ? (
              <span className="flex items-center justify-center gap-1.5">
                <Target className="h-3.5 w-3.5" aria-hidden="true" />
                Активные
                {activeMissions.length > 0 && (
                  <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-primary">
                    {activeMissions.length}
                  </span>
                )}
              </span>
            ) : (
              <span className="flex items-center justify-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                Завершённые
                {completedMissions.length > 0 && (
                  <span className="rounded-full bg-success/10 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-success">
                    {completedMissions.length}
                  </span>
                )}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Loading */}
      {isLoading && <MissionsSkeleton />}

      {/* Error */}
      {!isLoading && isError && (
        <div
          className="flex flex-col items-center gap-3 rounded-2xl border border-destructive/20 bg-destructive/5 py-14 text-center"
          role="alert"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <AlertCircle
              className="h-6 w-6 text-destructive"
              aria-hidden="true"
              strokeWidth={1.5}
            />
          </div>
          <div>
            <p className="text-sm font-medium text-destructive">
              Не удалось загрузить миссии
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Проверьте подключение и попробуйте снова
            </p>
          </div>
          <button
            type="button"
            onClick={() => void refetch()}
            className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            Повторить
          </button>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && displayedMissions.length === 0 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col items-center gap-3 rounded-2xl border border-border bg-card py-16 text-center"
        >
          <Sparkles
            className="h-10 w-10 text-muted-foreground/30"
            strokeWidth={1.5}
            aria-hidden="true"
          />
          <div className="max-w-[260px]">
            <p className="text-sm font-medium text-muted-foreground">
              {tab === "active"
                ? "Нет активных миссий"
                : "Нет завершённых миссий"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground/60">
              {tab === "active"
                ? "Новая миссия будет доступна на дашборде"
                : "Завершите первую миссию, чтобы она появилась здесь"}
            </p>
          </div>
          {tab === "active" && (
            <Link
              href="/dashboard"
              className="mt-2 rounded-lg border border-border bg-card px-4 py-2 text-xs font-medium text-foreground transition-colors hover:bg-muted/30"
            >
              Перейти на дашборд
            </Link>
          )}
        </motion.div>
      )}

      {/* Mission list */}
      {!isLoading && !isError && displayedMissions.length > 0 && (
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="space-y-3"
          >
            {displayedMissions.map((mission, i) => (
              <MissionCard key={mission.id} mission={mission} index={i} />
            ))}
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  );
}
