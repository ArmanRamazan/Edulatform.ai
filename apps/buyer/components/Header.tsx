"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { useDueCount } from "@/hooks/use-flashcards";
import { useMyXp, useMyStreak } from "@/hooks/use-gamification";
import { identity as identityApi } from "@/lib/api";

const AICreditIndicator = dynamic(
  () => import("@/components/AICreditIndicator").then((m) => ({ default: m.AICreditIndicator })),
  { ssr: false },
);

const ROLE_LABELS: Record<string, string> = {
  student: "Студент",
  teacher: "Преподаватель",
  admin: "Администратор",
};

export function Header() {
  const { user, token, loading, logout } = useAuth();
  const dueCount = useDueCount(token);
  const totalXp = useMyXp(token);
  const streak = useMyStreak(token);

  async function handleResend() {
    if (!token) return;
    await identityApi.resendVerification(token);
  }

  return (
    <>
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link href="/" className="text-xl font-bold">
            EduPlatform
          </Link>

          <nav className="flex items-center gap-4">
            <Link href="/" className="text-sm hover:underline">
              Курсы
            </Link>

            {loading ? (
              <span className="text-sm text-gray-400">...</span>
            ) : user ? (
              <>
                {user.role === "teacher" ? (
                  <Link href="/my-courses" className="text-sm hover:underline">
                    Мои курсы
                  </Link>
                ) : (
                  <Link href="/enrollments" className="text-sm hover:underline">
                    Мои курсы
                  </Link>
                )}
                {user.role === "student" && (
                  <Link href="/flashcards" className="relative text-sm hover:underline">
                    Повторение
                    {(dueCount.data ?? 0) > 0 && (
                      <span className="absolute -right-3 -top-2 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                        {dueCount.data}
                      </span>
                    )}
                  </Link>
                )}
                <Link href="/notifications" className="text-sm hover:underline">
                  Уведомления
                </Link>
                {user.role === "teacher" && user.is_verified && (
                  <Link href="/courses/new" className="text-sm hover:underline">
                    Создать курс
                  </Link>
                )}
                {user.role === "admin" && (
                  <Link href="/admin/teachers" className="text-sm hover:underline">
                    Панель админа
                  </Link>
                )}
                {user.role === "student" && (
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1 rounded bg-purple-100 px-2 py-0.5 text-xs font-semibold text-purple-700">
                      XP {totalXp.data ?? 0}
                    </span>
                    {(streak.data?.current_streak ?? 0) > 0 ? (
                      <Link
                        href="/badges"
                        className="flex items-center gap-1 rounded bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-700"
                        title={`Серия: ${streak.data?.current_streak} дн.`}
                      >
                        <span className="text-sm">&#x1F525;</span>
                        {streak.data?.current_streak}
                      </Link>
                    ) : (
                      <span
                        className="flex items-center gap-1 rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-400"
                        title="Нет активной серии"
                      >
                        <span className="text-sm">&#x1F525;</span>
                        0
                      </span>
                    )}
                    <AICreditIndicator token={token} />
                  </div>
                )}
                <span className="text-sm text-gray-500">{user.name}</span>
                <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                  {ROLE_LABELS[user.role] || user.role}
                </span>
                <button
                  onClick={logout}
                  className="rounded bg-gray-200 px-3 py-1 text-sm hover:bg-gray-300"
                >
                  Выйти
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
                >
                  Войти
                </Link>
                <Link href="/register" className="text-sm hover:underline">
                  Регистрация
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      {user && !user.email_verified && (
        <div className="border-b border-yellow-200 bg-yellow-50 px-4 py-2 text-center text-sm text-yellow-800">
          Подтвердите email для полного доступа.{" "}
          <button onClick={handleResend} className="underline hover:no-underline">
            Отправить повторно
          </button>
        </div>
      )}
    </>
  );
}
