"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertCircle,
  ArrowRight,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  ChevronLeft,
  Clock,
  GraduationCap,
  Layers,
  RotateCcw,
  Star,
  Trophy,
  Users,
  Zap,
} from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useCourseList } from "@/hooks/use-courses";
import { useEnroll, useMyEnrollments } from "@/hooks/use-enrollments";
import type { Course } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const TOTAL_STEPS = 5;
const STEP_LABELS = ["Добро\u00a0пожаловать", "Ваша\u00a0роль", "Первый\u00a0курс", "Цель", "Готово!"];

// ─────────────────────────────────────────────────────────────────────────────
// Step Indicator
// ─────────────────────────────────────────────────────────────────────────────

interface StepIndicatorProps {
  current: number;
}

function StepIndicator({ current }: StepIndicatorProps) {
  const progress = ((current - 1) / (TOTAL_STEPS - 1)) * 100;

  return (
    <div
      className="mb-10 w-full"
      role="progressbar"
      aria-valuenow={current}
      aria-valuemin={1}
      aria-valuemax={TOTAL_STEPS}
      aria-label={`Шаг ${current} из ${TOTAL_STEPS}: ${STEP_LABELS[current - 1]}`}
    >
      {/* Circles + connector lines */}
      <div className="flex w-full items-center">
        {[1, 2, 3, 4, 5].map((s, i) => {
          const isCompleted = s < current;
          const isActive = s === current;
          return (
            <React.Fragment key={s}>
              {/* Circle */}
              <div className="flex shrink-0 flex-col items-center gap-2">
                <motion.div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-semibold transition-colors duration-300",
                    isCompleted && "border-success bg-success text-white",
                    isActive &&
                      "border-primary bg-primary text-white",
                    !isCompleted && !isActive && "border-border bg-background text-muted-foreground",
                  )}
                  animate={
                    isActive
                      ? {
                          boxShadow: [
                            "0 0 0 0px rgba(124,92,252,0.4)",
                            "0 0 0 6px rgba(124,92,252,0.08)",
                            "0 0 0 0px rgba(124,92,252,0.4)",
                          ],
                        }
                      : { boxShadow: "0 0 0 0px rgba(124,92,252,0)" }
                  }
                  transition={{ duration: 2, repeat: isActive ? Infinity : 0 }}
                  initial={false}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="h-4 w-4" strokeWidth={2.5} />
                  ) : (
                    <span>{s}</span>
                  )}
                </motion.div>
                <span
                  className={cn(
                    "hidden text-[10px] font-medium leading-none sm:block",
                    isActive ? "text-primary" : "text-muted-foreground",
                  )}
                >
                  {STEP_LABELS[s - 1]}
                </span>
              </div>

              {/* Connector line */}
              {i < TOTAL_STEPS - 1 && (
                <div className="relative mx-1 h-px flex-1">
                  <div className="absolute inset-0 bg-border" />
                  <motion.div
                    className="absolute inset-y-0 left-0"
                    style={{
                      background: "linear-gradient(90deg, #7c5cfc, #a78bfa)",
                      boxShadow: "0 0 4px rgba(124,92,252,0.5)",
                    }}
                    animate={{ width: s < current ? "100%" : "0%" }}
                    transition={{ duration: 0.4, ease: "easeInOut" }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Thin progress bar below */}
      <div className="mt-5 h-0.5 w-full overflow-hidden rounded-full bg-border">
        <motion.div
          className="h-full rounded-full"
          style={{
            background: "linear-gradient(90deg, #7c5cfc 0%, #a78bfa 100%)",
            boxShadow: "0 0 6px rgba(124,92,252,0.4)",
          }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: "easeInOut" }}
        />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Step 1 — Welcome
// ─────────────────────────────────────────────────────────────────────────────

const WELCOME_FEATURES = [
  {
    icon: BrainCircuit,
    label: "AI-граф знаний",
    desc: "Концепции, связанные в карту — видите что знаете и что нет",
    iconClass: "text-primary",
    bgClass: "bg-primary/10",
  },
  {
    icon: BookOpen,
    label: "Миссии и флеш-карточки",
    desc: "Интерактивное обучение с FSRS-алгоритмом интервального повторения",
    iconClass: "text-info",
    bgClass: "bg-info/10",
  },
  {
    icon: Trophy,
    label: "XP, серии и значки",
    desc: "Прогресс виден команде — учиться интересно",
    iconClass: "text-warning",
    bgClass: "bg-warning/10",
  },
] as const;

interface StepWelcomeProps {
  onNext: () => void;
}

function StepWelcome({ onNext }: StepWelcomeProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Enter") onNext();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onNext]);

  return (
    <div className="text-center">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
          <Zap className="h-3 w-3" />
          KnowledgeOS
        </div>
        <h1 className="mb-3 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          Добро пожаловать в базу знаний
        </h1>
        <p className="mb-10 text-muted-foreground">
          Настроим всё за 3 минуты — и вы будете готовы к работе
        </p>
      </motion.div>

      <motion.ul
        className="mx-auto mb-10 max-w-md space-y-3 text-left"
        initial="hidden"
        animate="visible"
        variants={{
          visible: { transition: { staggerChildren: 0.1, delayChildren: 0.15 } },
          hidden: {},
        }}
      >
        {WELCOME_FEATURES.map(({ icon: Icon, label, desc, iconClass, bgClass }) => (
          <motion.li
            key={label}
            variants={{
              hidden: { opacity: 0, x: -14 },
              visible: { opacity: 1, x: 0 },
            }}
            transition={{ duration: 0.35 }}
            className="flex items-start gap-3 rounded-xl border border-border bg-card p-4"
          >
            <div className={cn("mt-0.5 rounded-lg p-2", bgClass)}>
              <Icon className={cn("h-4 w-4", iconClass)} />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">{label}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{desc}</p>
            </div>
          </motion.li>
        ))}
      </motion.ul>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <Button
          onClick={onNext}
          size="lg"
          className="gap-2 bg-primary px-8 shadow-[0_0_20px_rgba(124,92,252,0.3)] hover:bg-primary/90 hover:shadow-[0_0_28px_rgba(124,92,252,0.45)]"
        >
          Начать
          <ArrowRight className="h-4 w-4" />
        </Button>
        <p className="mt-3 text-xs text-muted-foreground">
          Нажмите <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">Enter</kbd> для продолжения
        </p>
      </motion.div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Step 2 — Role
// ─────────────────────────────────────────────────────────────────────────────

const ROLES = [
  {
    id: "engineer",
    icon: Layers,
    label: "Инженер",
    desc: "Изучаю технологии, прохожу миссии, слежу за своим прогрессом",
  },
  {
    id: "tech_lead",
    icon: Users,
    label: "Tech Lead",
    desc: "Управляю базой знаний команды, вижу аналитику по покрытию",
  },
] as const;

interface StepRoleProps {
  value: string | null;
  onChange: (v: string) => void;
  onNext: () => void;
  onBack: () => void;
}

function StepRole({ value, onChange, onNext, onBack }: StepRoleProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Enter" && value) onNext();
      if (e.key === "Escape") onBack();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [value, onNext, onBack]);

  return (
    <div>
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8 text-center"
      >
        <h2 className="mb-2 text-2xl font-bold tracking-tight text-foreground">
          Кто вы в команде?
        </h2>
        <p className="text-muted-foreground">
          Настроим интерфейс и уведомления под ваши задачи
        </p>
      </motion.div>

      <motion.div
        className="mx-auto grid max-w-lg gap-3 sm:grid-cols-2"
        initial="hidden"
        animate="visible"
        variants={{
          visible: { transition: { staggerChildren: 0.1 } },
          hidden: {},
        }}
      >
        {ROLES.map(({ id, icon: Icon, label, desc }) => (
          <motion.button
            key={id}
            type="button"
            onClick={() => onChange(id)}
            variants={{ hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0 } }}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.97 }}
            className={cn(
              "rounded-xl border-2 p-5 text-left outline-none transition-all duration-200",
              "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              value === id
                ? "border-primary bg-primary/10 shadow-[0_0_20px_rgba(124,92,252,0.2)]"
                : "border-border bg-card hover:border-primary/50",
            )}
          >
            <div
              className={cn(
                "mb-3 inline-flex rounded-lg p-2 transition-colors",
                value === id ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground",
              )}
            >
              <Icon className="h-5 w-5" />
            </div>
            <p className="mb-1 font-semibold text-foreground">{label}</p>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </motion.button>
        ))}
      </motion.div>

      <div className="mt-8 flex items-center justify-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack} className="gap-1">
          <ChevronLeft className="h-4 w-4" />
          Назад
        </Button>
        <Button
          onClick={onNext}
          disabled={!value}
          className="gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40"
        >
          Продолжить
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Step 3 — Pick Course
// ─────────────────────────────────────────────────────────────────────────────

const LEVEL_META: Record<string, { label: string; colorClass: string }> = {
  beginner: { label: "Начальный", colorClass: "text-success" },
  intermediate: { label: "Средний", colorClass: "text-warning" },
  advanced: { label: "Продвинутый", colorClass: "text-destructive" },
};

function CourseCardSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <Skeleton className="mb-3 h-4 w-3/4" />
      <Skeleton className="mb-3 h-3 w-1/2" />
      <div className="flex gap-2">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-12 rounded-full" />
      </div>
    </div>
  );
}

interface CoursePickCardProps {
  course: Course;
  selected: boolean;
  onSelect: () => void;
}

function CoursePickCard({ course, selected, onSelect }: CoursePickCardProps) {
  const meta = LEVEL_META[course.level];
  return (
    <motion.button
      type="button"
      onClick={onSelect}
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.97 }}
      className={cn(
        "w-full rounded-xl border-2 p-4 text-left outline-none transition-all duration-200",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        selected
          ? "border-primary bg-primary/10 shadow-[0_0_20px_rgba(124,92,252,0.2)]"
          : "border-border bg-card hover:border-primary/40",
      )}
    >
      <p className="mb-2 line-clamp-2 text-sm font-semibold text-foreground">
        {course.title}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {meta && (
          <span className={cn("text-xs font-medium", meta.colorClass)}>{meta.label}</span>
        )}
        {course.duration_minutes && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            {course.duration_minutes}\u00a0мин
          </span>
        )}
        {course.avg_rating != null && (
          <span className="flex items-center gap-1 text-xs text-warning">
            <Star className="h-3 w-3 fill-current" />
            {course.avg_rating.toFixed(1)}
          </span>
        )}
      </div>
    </motion.button>
  );
}

interface StepPickCourseProps {
  token: string | null;
  onNext: (enrolledCourseId: string | null) => void;
  onBack: () => void;
}

function StepPickCourse({ token, onNext, onBack }: StepPickCourseProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [enrollError, setEnrollError] = useState("");
  const { data, isLoading, isError, refetch } = useCourseList({
    is_free: true,
    sort_by: "avg_rating",
    limit: 6,
  });
  const enroll = useEnroll(token);

  const handleEnroll = useCallback(async () => {
    if (!selectedId) return;
    setEnrollError("");
    try {
      await enroll.mutateAsync({ course_id: selectedId });
      onNext(selectedId);
    } catch {
      setEnrollError("Не удалось записаться. Попробуйте ещё раз.");
    }
  }, [selectedId, enroll, onNext]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Enter" && selectedId && !enroll.isPending) void handleEnroll();
      if (e.key === "Escape") onBack();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [selectedId, enroll.isPending, handleEnroll, onBack]);

  const courseList = data?.items ?? [];

  return (
    <div>
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 text-center"
      >
        <h2 className="mb-2 text-2xl font-bold tracking-tight text-foreground">
          Выберите первый курс
        </h2>
        <p className="text-sm text-muted-foreground">Все курсы ниже — бесплатные</p>
      </motion.div>

      {enrollError && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="mb-4 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
        >
          <AlertCircle className="h-4 w-4 shrink-0" />
          {enrollError}
        </motion.div>
      )}

      {isError ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center gap-4 py-12 text-center"
        >
          <AlertCircle className="h-12 w-12 text-muted-foreground" />
          <div>
            <p className="font-medium text-foreground">Не удалось загрузить курсы</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Проверьте соединение и попробуйте снова
            </p>
          </div>
          <Button variant="outline" onClick={() => void refetch()} className="gap-2">
            <RotateCcw className="h-4 w-4" />
            Попробовать снова
          </Button>
        </motion.div>
      ) : isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <CourseCardSkeleton key={i} />
          ))}
        </div>
      ) : courseList.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center gap-3 py-12 text-center"
        >
          <BookOpen className="h-12 w-12 text-muted-foreground" />
          <p className="font-medium text-foreground">Курсы пока недоступны</p>
          <p className="text-sm text-muted-foreground">
            Скоро здесь появятся бесплатные курсы для старта
          </p>
        </motion.div>
      ) : (
        <motion.div
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
          initial="hidden"
          animate="visible"
          variants={{
            visible: { transition: { staggerChildren: 0.05 } },
            hidden: {},
          }}
        >
          {courseList.map((course: Course) => (
            <motion.div
              key={course.id}
              variants={{ hidden: { opacity: 0, y: 8 }, visible: { opacity: 1, y: 0 } }}
            >
              <CoursePickCard
                course={course}
                selected={selectedId === course.id}
                onSelect={() => setSelectedId(course.id)}
              />
            </motion.div>
          ))}
        </motion.div>
      )}

      <div className="mt-8 flex flex-col items-center gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBack} className="gap-1">
            <ChevronLeft className="h-4 w-4" />
            Назад
          </Button>
          <Button
            onClick={() => void handleEnroll()}
            disabled={!selectedId || enroll.isPending}
            className="gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40"
          >
            {enroll.isPending ? "Записываем..." : "Записаться и продолжить"}
            {!enroll.isPending && <ArrowRight className="h-4 w-4" />}
          </Button>
        </div>
        <button
          type="button"
          onClick={() => onNext(null)}
          className="text-xs text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline"
        >
          Пропустить этот шаг
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Step 4 — Weekly Goal
// ─────────────────────────────────────────────────────────────────────────────

const GOALS = [
  { id: "casual", label: "1–2\u00a0ч / нед", desc: "Лёгкий темп", emoji: "🌱" },
  { id: "regular", label: "3–5\u00a0ч / нед", desc: "Стабильный рост", emoji: "🔥" },
  { id: "intense", label: "5–10\u00a0ч / нед", desc: "Быстрый прогресс", emoji: "⚡" },
  { id: "deep", label: "10+\u00a0ч / нед", desc: "Полное погружение", emoji: "🚀" },
] as const;

interface StepGoalProps {
  value: string | null;
  onChange: (v: string) => void;
  onNext: () => void;
  onBack: () => void;
}

function StepGoal({ value, onChange, onNext, onBack }: StepGoalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Enter" && value) onNext();
      if (e.key === "Escape") onBack();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [value, onNext, onBack]);

  return (
    <div>
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8 text-center"
      >
        <h2 className="mb-2 text-2xl font-bold tracking-tight text-foreground">
          Сколько времени готовы уделять?
        </h2>
        <p className="text-muted-foreground">
          Настроим ритм уведомлений и напоминаний
        </p>
      </motion.div>

      <motion.div
        className="mx-auto grid max-w-lg gap-3 sm:grid-cols-2"
        initial="hidden"
        animate="visible"
        variants={{
          visible: { transition: { staggerChildren: 0.08 } },
          hidden: {},
        }}
      >
        {GOALS.map(({ id, label, desc, emoji }) => (
          <motion.button
            key={id}
            type="button"
            onClick={() => onChange(id)}
            variants={{ hidden: { opacity: 0, scale: 0.95 }, visible: { opacity: 1, scale: 1 } }}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.97 }}
            className={cn(
              "rounded-xl border-2 p-5 text-left outline-none transition-all duration-200",
              "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              value === id
                ? "border-primary bg-primary/10 shadow-[0_0_20px_rgba(124,92,252,0.2)]"
                : "border-border bg-card hover:border-primary/40",
            )}
          >
            <span className="mb-2 block text-2xl" role="img" aria-hidden="true">
              {emoji}
            </span>
            <p className="font-semibold text-foreground">{label}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{desc}</p>
          </motion.button>
        ))}
      </motion.div>

      <div className="mt-8 flex items-center justify-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack} className="gap-1">
          <ChevronLeft className="h-4 w-4" />
          Назад
        </Button>
        <Button
          onClick={onNext}
          disabled={!value}
          className="gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40"
        >
          Завершить настройку
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Step 5 — Done
// ─────────────────────────────────────────────────────────────────────────────

const DONE_LINKS = [
  {
    href: "/courses",
    icon: GraduationCap,
    label: "Уроки с AI-объяснениями",
    desc: "Интерактивное обучение с AI-тьютором",
    iconClass: "text-primary",
    bgClass: "bg-primary/10",
  },
  {
    href: "/flashcards",
    icon: Layers,
    label: "Повторение через флеш-карточки",
    desc: "Запоминайте материал эффективнее с FSRS",
    iconClass: "text-info",
    bgClass: "bg-info/10",
  },
  {
    href: "/badges",
    icon: Trophy,
    label: "Прогресс и XP",
    desc: "Значки, серии и командный рейтинг",
    iconClass: "text-warning",
    bgClass: "bg-warning/10",
  },
] as const;

interface StepDoneProps {
  enrolledCourseId: string | null;
}

function StepDone({ enrolledCourseId }: StepDoneProps) {
  const courseLink = enrolledCourseId ? `/courses/${enrolledCourseId}` : "/courses";
  const links = [{ ...DONE_LINKS[0], href: courseLink }, ...DONE_LINKS.slice(1)];

  return (
    <div className="text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.5 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 200, damping: 14 }}
        className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-success/15 ring-1 ring-success/30"
      >
        <CheckCircle2 className="h-8 w-8 text-success" />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mb-8"
      >
        <h2 className="mb-2 text-2xl font-bold tracking-tight text-foreground">
          Всё готово!
        </h2>
        <p className="text-muted-foreground">Начните исследовать базу знаний прямо сейчас</p>
      </motion.div>

      <motion.div
        className="mx-auto mb-8 grid max-w-lg gap-3"
        initial="hidden"
        animate="visible"
        variants={{
          visible: { transition: { staggerChildren: 0.1, delayChildren: 0.3 } },
          hidden: {},
        }}
      >
        {links.map(({ href, icon: Icon, label, desc, iconClass, bgClass }) => (
          <motion.div
            key={href}
            variants={{ hidden: { opacity: 0, x: -12 }, visible: { opacity: 1, x: 0 } }}
          >
            <Link
              href={href}
              className="flex items-center gap-3 rounded-xl border border-border bg-card p-4 text-left transition-all hover:border-primary/50 hover:bg-muted/30"
            >
              <div className={cn("shrink-0 rounded-lg p-2", bgClass)}>
                <Icon className={cn("h-5 w-5", iconClass)} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground">{label}</p>
                <p className="text-xs text-muted-foreground">{desc}</p>
              </div>
              <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
            </Link>
          </motion.div>
        ))}
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.7 }}
      >
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-8 py-3 font-medium text-white shadow-[0_0_20px_rgba(124,92,252,0.35)] transition-all hover:bg-primary/90 hover:shadow-[0_0_28px_rgba(124,92,252,0.5)]"
        >
          Перейти в дашборд
          <ArrowRight className="h-4 w-4" />
        </Link>
      </motion.div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Loading skeleton (matches final layout — no spinner)
// ─────────────────────────────────────────────────────────────────────────────

function OnboardingPageSkeleton() {
  return (
    <main className="mx-auto min-h-screen max-w-2xl px-4 py-8">
      {/* Step indicator */}
      <div className="mb-10 flex w-full items-center">
        {[1, 2, 3, 4, 5].map((i, idx) => (
          <React.Fragment key={i}>
            <div className="flex shrink-0 flex-col items-center gap-2">
              <Skeleton className="h-8 w-8 rounded-full" />
              <Skeleton className="hidden h-2.5 w-14 sm:block" />
            </div>
            {idx < 4 && <Skeleton className="mx-1 h-px flex-1" />}
          </React.Fragment>
        ))}
      </div>
      <Skeleton className="mb-10 h-0.5 w-full" />

      {/* Content */}
      <div className="space-y-4 text-center">
        <Skeleton className="mx-auto h-6 w-28 rounded-full" />
        <Skeleton className="mx-auto h-9 w-3/4 rounded-lg" />
        <Skeleton className="mx-auto h-4 w-1/2" />
        <div className="mt-8 space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[72px] w-full rounded-xl" />
          ))}
        </div>
        <Skeleton className="mx-auto mt-6 h-10 w-36 rounded-md" />
      </div>
    </main>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Step transition variants
// ─────────────────────────────────────────────────────────────────────────────

const stepVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 48 : -48,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction > 0 ? -48 : 48,
    opacity: 0,
  }),
};

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const router = useRouter();
  const { user, token, loading } = useAuth();
  const { data: enrollmentsData } = useMyEnrollments(token, { limit: 1, offset: 4 });

  const [step, setStep] = useState(1);
  const [direction, setDirection] = useState(1);
  const [enrolledCourseId, setEnrolledCourseId] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [goal, setGoal] = useState<string | null>(null);

  const goNext = useCallback(() => {
    setDirection(1);
    setStep((s) => Math.min(s + 1, TOTAL_STEPS));
  }, []);

  const goBack = useCallback(() => {
    setDirection(-1);
    setStep((s) => Math.max(s - 1, 1));
  }, []);

  if (loading) return <OnboardingPageSkeleton />;

  if (!user) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <GraduationCap className="h-6 w-6 text-muted-foreground" />
        </div>
        <p className="text-muted-foreground">Для начала нужно зарегистрироваться</p>
        <Link href="/register">
          <Button className="bg-primary hover:bg-primary/90">Регистрация</Button>
        </Link>
      </main>
    );
  }

  const hasEnrollments = (enrollmentsData?.items?.length ?? 0) > 0;
  if (hasEnrollments) {
    router.replace("/");
    return null;
  }

  return (
    <>
      {/* Ambient background glow */}
      <div
        className="pointer-events-none fixed inset-0 -z-10"
        aria-hidden="true"
      >
        <div className="absolute left-1/2 top-1/3 h-[500px] w-[700px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/5 blur-3xl" />
      </div>

      <main className="mx-auto min-h-screen max-w-2xl px-4 py-8">
        <StepIndicator current={step} />

        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={step}
            custom={direction}
            variants={stepVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.22, ease: "easeInOut" }}
          >
            {step === 1 && <StepWelcome onNext={goNext} />}

            {step === 2 && (
              <StepRole
                value={role}
                onChange={setRole}
                onNext={goNext}
                onBack={goBack}
              />
            )}

            {step === 3 && (
              <StepPickCourse
                token={token}
                onNext={(courseId) => {
                  setEnrolledCourseId(courseId);
                  goNext();
                }}
                onBack={goBack}
              />
            )}

            {step === 4 && (
              <StepGoal
                value={goal}
                onChange={setGoal}
                onNext={goNext}
                onBack={goBack}
              />
            )}

            {step === 5 && <StepDone enrolledCourseId={enrolledCourseId} />}
          </motion.div>
        </AnimatePresence>
      </main>
    </>
  );
}
