"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { useCourseList } from "@/hooks/use-courses";
import { useEnroll, useMyEnrollments } from "@/hooks/use-enrollments";
import type { Course } from "@/lib/api";

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center justify-center gap-2 py-6">
      {[1, 2, 3].map((s) => (
        <div
          key={s}
          className={`h-2.5 w-2.5 rounded-full transition-colors ${
            s === current ? "bg-blue-600" : s < current ? "bg-blue-300" : "bg-gray-200"
          }`}
        />
      ))}
      <span className="ml-2 text-sm text-gray-400">Шаг {current} из 3</span>
    </div>
  );
}

function StepWelcome({ onNext }: { onNext: () => void }) {
  return (
    <div className="text-center">
      <h1 className="mb-4 text-3xl font-bold text-gray-900">
        Добро пожаловать в EduPlatform!
      </h1>
      <p className="mb-8 text-gray-500">
        Вот что вас ждёт:
      </p>
      <ul className="mx-auto mb-10 max-w-md space-y-4 text-left">
        <li className="flex items-start gap-3 rounded-lg bg-blue-50 p-4">
          <span className="text-2xl" role="img" aria-label="books">📚</span>
          <span className="text-gray-700">
            Сотни курсов по программированию, дизайну и бизнесу
          </span>
        </li>
        <li className="flex items-start gap-3 rounded-lg bg-purple-50 p-4">
          <span className="text-2xl" role="img" aria-label="robot">🤖</span>
          <span className="text-gray-700">
            AI-тьютор, тесты и флеш-карточки для эффективного обучения
          </span>
        </li>
        <li className="flex items-start gap-3 rounded-lg bg-amber-50 p-4">
          <span className="text-2xl" role="img" aria-label="trophy">🏆</span>
          <span className="text-gray-700">
            XP, серии и значки — учиться интересно
          </span>
        </li>
      </ul>
      <button
        onClick={onNext}
        className="rounded-lg bg-blue-600 px-8 py-3 text-lg font-medium text-white hover:bg-blue-700 transition-colors"
      >
        Начать
      </button>
    </div>
  );
}

function CourseCard({
  course,
  selected,
  onSelect,
}: {
  course: Course;
  selected: boolean;
  onSelect: () => void;
}) {
  const levelLabels: Record<string, string> = {
    beginner: "Начальный",
    intermediate: "Средний",
    advanced: "Продвинутый",
  };
  const levelColors: Record<string, string> = {
    beginner: "bg-green-100 text-green-700",
    intermediate: "bg-yellow-100 text-yellow-700",
    advanced: "bg-red-100 text-red-700",
  };

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-xl border-2 p-4 text-left transition-all hover:shadow-md ${
        selected ? "border-blue-500 bg-blue-50 shadow-md" : "border-gray-200 bg-white"
      }`}
    >
      <h3 className="mb-2 font-semibold text-gray-900 line-clamp-2">{course.title}</h3>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${levelColors[course.level] ?? "bg-gray-100 text-gray-600"}`}>
          {levelLabels[course.level] ?? course.level}
        </span>
        <span className="text-xs text-gray-500">{course.duration_minutes} мин</span>
        {course.avg_rating != null && (
          <span className="text-xs text-amber-600">★ {course.avg_rating.toFixed(1)}</span>
        )}
      </div>
      <span className="mt-2 inline-block rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
        Бесплатно
      </span>
    </button>
  );
}

function StepPickCourse({
  token,
  onNext,
}: {
  token: string | null;
  onNext: (enrolledCourseId: string | null) => void;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const { data, isLoading } = useCourseList({
    is_free: true,
    sort_by: "avg_rating",
    limit: 6,
  });
  const enroll = useEnroll(token);

  async function handleEnroll() {
    if (!selectedId) return;
    setError("");
    try {
      await enroll.mutateAsync({ course_id: selectedId });
      onNext(selectedId);
    } catch {
      setError("Не удалось записаться. Попробуйте ещё раз.");
    }
  }

  const courseList = data?.items ?? [];

  return (
    <div className="text-center">
      <h1 className="mb-2 text-2xl font-bold text-gray-900">Выберите первый курс</h1>
      <p className="mb-6 text-gray-500">Все курсы ниже — бесплатные</p>

      {error && (
        <div className="mb-4 rounded bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl bg-gray-100" />
          ))}
        </div>
      ) : courseList.length === 0 ? (
        <p className="py-8 text-gray-400">Пока нет доступных бесплатных курсов</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {courseList.map((course: Course) => (
            <CourseCard
              key={course.id}
              course={course}
              selected={selectedId === course.id}
              onSelect={() => setSelectedId(course.id)}
            />
          ))}
        </div>
      )}

      <div className="mt-8 flex flex-col items-center gap-3">
        <button
          onClick={handleEnroll}
          disabled={!selectedId || enroll.isPending}
          className="rounded-lg bg-blue-600 px-8 py-3 font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {enroll.isPending ? "Записываем..." : "Записаться и начать"}
        </button>
        <button
          onClick={() => onNext(null)}
          className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
        >
          Пропустить
        </button>
      </div>
    </div>
  );
}

function StepDone({ enrolledCourseId }: { enrolledCourseId: string | null }) {
  const courseLink = enrolledCourseId ? `/courses/${enrolledCourseId}` : "/courses";

  return (
    <div className="text-center">
      <h1 className="mb-2 text-2xl font-bold text-gray-900">
        Готово! Начните учиться прямо сейчас
      </h1>
      <p className="mb-8 text-gray-500">Вот что вам доступно:</p>

      <div className="mx-auto mb-10 grid max-w-lg gap-4">
        <Link
          href={courseLink}
          className="flex items-start gap-3 rounded-xl border border-gray-200 p-4 text-left hover:bg-gray-50 transition-colors"
        >
          <span className="text-2xl">🎓</span>
          <div>
            <p className="font-medium text-gray-900">Уроки с AI-объяснениями</p>
            <p className="text-sm text-gray-500">Интерактивное обучение с AI-тьютором</p>
          </div>
        </Link>
        <Link
          href="/flashcards"
          className="flex items-start gap-3 rounded-xl border border-gray-200 p-4 text-left hover:bg-gray-50 transition-colors"
        >
          <span className="text-2xl">🃏</span>
          <div>
            <p className="font-medium text-gray-900">Повторение через флеш-карточки</p>
            <p className="text-sm text-gray-500">Запоминайте материал эффективнее</p>
          </div>
        </Link>
        <Link
          href="/badges"
          className="flex items-start gap-3 rounded-xl border border-gray-200 p-4 text-left hover:bg-gray-50 transition-colors"
        >
          <span className="text-2xl">⭐</span>
          <div>
            <p className="font-medium text-gray-900">Отслеживайте прогресс и зарабатывайте XP</p>
            <p className="text-sm text-gray-500">Значки, серии и рейтинг</p>
          </div>
        </Link>
      </div>

      <Link
        href="/"
        className="inline-block rounded-lg bg-blue-600 px-8 py-3 font-medium text-white hover:bg-blue-700 transition-colors"
      >
        Перейти к курсам
      </Link>
    </div>
  );
}

export default function OnboardingPage() {
  const router = useRouter();
  const { user, token, loading } = useAuth();
  const { data: enrollmentsData } = useMyEnrollments(token, { limit: 1, offset: 4 });
  const [step, setStep] = useState(1);
  const [enrolledCourseId, setEnrolledCourseId] = useState<string | null>(null);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </main>
    );
  }

  if (!user) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p className="text-gray-500">Для начала нужно зарегистрироваться</p>
        <Link
          href="/register"
          className="rounded-lg bg-blue-600 px-6 py-2 text-white hover:bg-blue-700"
        >
          Регистрация
        </Link>
      </main>
    );
  }

  const hasEnoughEnrollments = (enrollmentsData?.items?.length ?? 0) > 0;
  if (hasEnoughEnrollments) {
    router.replace("/");
    return null;
  }

  return (
    <main className="mx-auto min-h-screen max-w-2xl px-4 py-8">
      <StepIndicator current={step} />
      {step === 1 && <StepWelcome onNext={() => setStep(2)} />}
      {step === 2 && (
        <StepPickCourse
          token={token}
          onNext={(courseId) => {
            setEnrolledCourseId(courseId);
            setStep(3);
          }}
        />
      )}
      {step === 3 && <StepDone enrolledCourseId={enrolledCourseId} />}
    </main>
  );
}
