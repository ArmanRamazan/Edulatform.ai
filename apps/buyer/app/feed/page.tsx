"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useMyFollowing } from "@/hooks/use-profile";
import { useMyActivity, useSocialFeed } from "@/hooks/use-activity";
import { ActivityCard } from "@/components/ActivityCard";

type Tab = "my" | "following";

export default function FeedPage() {
  const { user, token, loading: authLoading } = useAuth();
  const [tab, setTab] = useState<Tab>("my");

  const myActivity = useMyActivity(token, { limit: 20 });
  const following = useMyFollowing(token);

  const followedUserIds = (following.data?.items ?? []).map((f) => f.following_id);

  const socialFeed = useSocialFeed(token, followedUserIds, { limit: 20 });

  if (authLoading) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 rounded bg-gray-200" />
          <div className="h-12 w-full rounded bg-gray-200" />
          <div className="h-24 w-full rounded bg-gray-200" />
        </div>
      </div>
    );
  }

  if (!user || !token) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <p className="text-gray-600">Войдите, чтобы просматривать ленту активности.</p>
      </div>
    );
  }

  const isMyTab = tab === "my";
  const activities = isMyTab ? myActivity.data?.items ?? [] : socialFeed.data?.items ?? [];
  const isLoading = isMyTab ? myActivity.isLoading : socialFeed.isLoading || following.isLoading;
  const isError = isMyTab ? myActivity.isError : socialFeed.isError;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">Лента активности</h1>

      <div className="mb-6 flex gap-2">
        <button
          onClick={() => setTab("my")}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            isMyTab
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          Моя активность
        </button>
        <button
          onClick={() => setTab("following")}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            !isMyTab
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          Подписки
        </button>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse rounded-lg border border-gray-200 bg-white p-4">
              <div className="flex items-start gap-3">
                <div className="h-10 w-10 rounded-full bg-gray-200" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-3/4 rounded bg-gray-200" />
                  <div className="h-3 w-1/4 rounded bg-gray-200" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {isError && (
        <p className="text-sm text-red-600">Не удалось загрузить ленту активности.</p>
      )}

      {!isLoading && !isError && !isMyTab && followedUserIds.length === 0 && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center">
          <p className="text-gray-600">
            Подпишитесь на преподавателей, чтобы видеть их активность
          </p>
        </div>
      )}

      {!isLoading && !isError && activities.length === 0 && (isMyTab || followedUserIds.length > 0) && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center">
          <p className="text-gray-600">
            {isMyTab ? "Пока нет активности." : "Нет активности от пользователей, на которых вы подписаны."}
          </p>
        </div>
      )}

      {!isLoading && !isError && activities.length > 0 && (
        <div className="space-y-3">
          {activities.map((a) => (
            <ActivityCard key={a.id} activity={a} />
          ))}
        </div>
      )}
    </div>
  );
}
