"use client";

import { use } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { FollowButton } from "@/components/FollowButton";
import { useAuth } from "@/hooks/use-auth";
import { useUserProfile, useFollowCounts } from "@/hooks/use-profile";

const ROLE_LABELS: Record<string, string> = {
  student: "Студент",
  teacher: "Преподаватель",
  admin: "Администратор",
};

function Initials({ name }: { name: string }) {
  const letters = name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return (
    <div className="flex h-20 w-20 items-center justify-center rounded-full bg-blue-100 text-2xl font-bold text-blue-600">
      {letters}
    </div>
  );
}

export default function UserProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user, token } = useAuth();

  const { data: profile, error: profileError, isLoading } = useUserProfile(id);
  const { data: followCounts } = useFollowCounts(id);

  const isOwnProfile = user?.id === id;

  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-4 py-6">
        <Link href="/" className="mb-4 inline-block text-sm text-blue-600 hover:underline">
          &larr; На главную
        </Link>

        {profileError ? (
          <div className="rounded bg-red-50 p-4 text-red-600">
            Профиль не найден или недоступен
          </div>
        ) : isLoading || !profile ? (
          <div className="space-y-4">
            <div className="h-20 w-20 animate-pulse rounded-full bg-gray-200" />
            <div className="h-6 w-48 animate-pulse rounded bg-gray-200" />
          </div>
        ) : (
          <>
            {/* Profile card */}
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <div className="flex items-start gap-5">
                {profile.avatar_url ? (
                  <img
                    src={profile.avatar_url}
                    alt={profile.name}
                    className="h-20 w-20 rounded-full object-cover"
                  />
                ) : (
                  <Initials name={profile.name} />
                )}
                <div className="flex-1">
                  <h1 className="text-2xl font-bold">{profile.name}</h1>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                      {ROLE_LABELS[profile.role] || profile.role}
                    </span>
                    {profile.is_verified && (
                      <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">
                        Подтверждённый
                      </span>
                    )}
                  </div>
                  {profile.bio && (
                    <p className="mt-3 text-sm text-gray-600">{profile.bio}</p>
                  )}
                  <p className="mt-2 text-xs text-gray-400">
                    На платформе с {new Date(profile.created_at).toLocaleDateString("ru", { year: "numeric", month: "long" })}
                  </p>
                </div>
              </div>

              {/* Stats row */}
              <div className="mt-5 flex items-center gap-6 border-t border-gray-100 pt-4">
                <div className="text-center">
                  <span className="block text-lg font-bold">
                    {followCounts?.followers_count ?? 0}
                  </span>
                  <span className="text-xs text-gray-500">подписчиков</span>
                </div>
                <div className="text-center">
                  <span className="block text-lg font-bold">
                    {followCounts?.following_count ?? 0}
                  </span>
                  <span className="text-xs text-gray-500">подписок</span>
                </div>
                <div className="ml-auto flex items-center gap-3">
                  {isOwnProfile ? (
                    <Link
                      href="/settings"
                      className="rounded border border-gray-200 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
                    >
                      Редактировать
                    </Link>
                  ) : (
                    <>
                      <FollowButton
                        token={token}
                        currentUserId={user?.id ?? null}
                        targetUserId={id}
                      />
                      {token && (
                        <Link
                          href={`/messages?to=${id}`}
                          className="rounded border border-blue-600 px-4 py-2 text-sm text-blue-600 hover:bg-blue-50"
                        >
                          Написать сообщение
                        </Link>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Role-specific sections */}
            {profile.role === "teacher" && (
              <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
                <h2 className="mb-2 text-lg font-bold">Курсы преподавателя</h2>
                <p className="text-sm text-gray-400">
                  Список курсов скоро будет доступен
                </p>
              </div>
            )}

            {profile.role === "student" && (
              <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
                <h2 className="mb-2 text-lg font-bold">Достижения</h2>
                <p className="text-sm text-gray-400">
                  Достижения скоро будут доступны
                </p>
              </div>
            )}
          </>
        )}
      </main>
    </>
  );
}
