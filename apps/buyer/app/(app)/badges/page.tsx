"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { useMyBadges, useMyXpHistory, useMyStreak } from "@/hooks/use-gamification";

const BADGE_ICONS: Record<string, string> = {
  first_enrollment: "\uD83C\uDF93",
  streak_7: "\uD83D\uDD25",
  quiz_ace: "\u2B50",
  mastery_100: "\uD83C\uDFC6",
};

const BADGE_LABELS: Record<string, string> = {
  first_enrollment: "Первый курс",
  streak_7: "7 дней подряд",
  quiz_ace: "Идеальный тест",
  mastery_100: "Полное мастерство",
};

const ALL_BADGES = ["first_enrollment", "streak_7", "quiz_ace", "mastery_100"];

export default function BadgesPage() {
  const { token, user, loading } = useAuth();
  const { data: badgeData, isLoading: badgesLoading } = useMyBadges(token);
  const { data: xpData, isLoading: xpLoading } = useMyXpHistory(token, { limit: 10 });
  const { data: streakData, isLoading: streakLoading } = useMyStreak(token);

  const unlockedTypes = new Set(badgeData?.badges.map((b) => b.badge_type) ?? []);

  return (
    <main className="mx-auto max-w-4xl px-4 py-6">
        <h1 className="mb-6 text-2xl font-bold">Достижения</h1>

        {loading || badgesLoading ? (
          <p className="text-gray-400">Загрузка...</p>
        ) : !user ? (
          <p className="text-gray-500">
            <Link href="/login" className="text-blue-600 hover:underline">
              Войдите
            </Link>{" "}
            чтобы увидеть достижения.
          </p>
        ) : (
          <div className="space-y-8">
            {/* Stats summary */}
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-lg border border-purple-200 bg-purple-50 p-4 text-center">
                <p className="text-2xl font-bold text-purple-700">{xpData?.total_xp ?? 0}</p>
                <p className="text-sm text-purple-600">Всего XP</p>
              </div>
              <div className="rounded-lg border border-orange-200 bg-orange-50 p-4 text-center">
                <p className="text-2xl font-bold text-orange-700">
                  {streakData?.current_streak ?? 0}
                </p>
                <p className="text-sm text-orange-600">Текущая серия (дн.)</p>
              </div>
              <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-center">
                <p className="text-2xl font-bold text-yellow-700">
                  {streakData?.longest_streak ?? 0}
                </p>
                <p className="text-sm text-yellow-600">Лучшая серия (дн.)</p>
              </div>
            </div>

            {/* Badge shelf */}
            <section>
              <h2 className="mb-4 text-lg font-semibold">Значки</h2>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {ALL_BADGES.map((type) => {
                  const unlocked = unlockedTypes.has(type);
                  const badge = badgeData?.badges.find((b) => b.badge_type === type);
                  return (
                    <div
                      key={type}
                      className={`flex flex-col items-center rounded-lg border p-4 ${
                        unlocked
                          ? "border-yellow-300 bg-yellow-50"
                          : "border-gray-200 bg-gray-50 opacity-50"
                      }`}
                    >
                      <span className="text-3xl">{BADGE_ICONS[type] ?? "\uD83C\uDFC5"}</span>
                      <p className="mt-2 text-center text-sm font-medium">
                        {BADGE_LABELS[type] ?? type}
                      </p>
                      {unlocked && badge ? (
                        <p className="mt-1 text-xs text-gray-500">
                          {new Date(badge.unlocked_at).toLocaleDateString("ru")}
                        </p>
                      ) : (
                        <p className="mt-1 text-xs text-gray-400">Не получен</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Recent XP events */}
            <section>
              <h2 className="mb-4 text-lg font-semibold">Последние XP</h2>
              {xpLoading ? (
                <p className="text-gray-400">Загрузка...</p>
              ) : !xpData || xpData.events.length === 0 ? (
                <p className="text-gray-500">Пока нет очков опыта.</p>
              ) : (
                <div className="space-y-2">
                  {xpData.events.map((ev, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between rounded border border-gray-200 px-4 py-2"
                    >
                      <div>
                        <span className="text-sm font-medium">{xpActionLabel(ev.action)}</span>
                        <span className="ml-2 text-xs text-gray-400">
                          {new Date(ev.created_at).toLocaleString("ru")}
                        </span>
                      </div>
                      <span className="font-semibold text-purple-700">+{ev.points} XP</span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </main>
  );
}

function xpActionLabel(action: string): string {
  switch (action) {
    case "lesson_complete":
      return "Урок пройден";
    case "quiz_submit":
      return "Тест выполнен";
    case "flashcard_review":
      return "Повторение карточки";
    default:
      return action;
  }
}
