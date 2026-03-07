"use client";

import { useState } from "react";
import { Activity, RefreshCw, Users } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useMyFollowing } from "@/hooks/use-profile";
import { useMyActivity, useSocialFeed } from "@/hooks/use-activity";
import { ActivityCard } from "@/components/ActivityCard";

type Tab = "my" | "following";

function FeedSkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading activity feed">
      {[1, 2, 3].map((i) => (
        <div key={i} className="relative overflow-hidden rounded-xl border border-border bg-card p-4">
          <div className="flex items-start gap-3">
            <div className="relative h-10 w-10 overflow-hidden rounded-full bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
            <div className="flex-1 space-y-2">
              <div className="relative h-4 w-3/4 overflow-hidden rounded bg-secondary">
                <div className="absolute inset-0 animate-shimmer" />
              </div>
              <div className="relative h-3 w-1/4 overflow-hidden rounded bg-secondary">
                <div className="absolute inset-0 animate-shimmer" />
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function FeedPage() {
  const { user, token, loading: authLoading } = useAuth();
  const [tab, setTab] = useState<Tab>("my");

  const myActivity = useMyActivity(token, { limit: 20 });
  const following = useMyFollowing(token);

  const followedUserIds = (following.data?.items ?? []).map((f) => f.following_id);
  const socialFeed = useSocialFeed(token, followedUserIds, { limit: 20 });

  const isMyTab = tab === "my";
  const activities = isMyTab ? myActivity.data?.items ?? [] : socialFeed.data?.items ?? [];
  const isLoading = isMyTab ? myActivity.isLoading : socialFeed.isLoading || following.isLoading;
  const isError = isMyTab ? myActivity.isError : socialFeed.isError;

  if (authLoading) {
    return (
      <div className="mx-auto max-w-2xl">
        <div className="relative mb-6 h-8 w-48 overflow-hidden rounded-lg bg-card border border-border">
          <div className="absolute inset-0 animate-shimmer" />
        </div>
        <FeedSkeleton />
      </div>
    );
  }

  if (!user || !token) {
    return (
      <div className="mx-auto max-w-2xl py-12 text-center">
        <Activity
          className="mx-auto mb-3 h-10 w-10 text-muted-foreground/30"
          aria-hidden="true"
          strokeWidth={1.5}
        />
        <p className="text-sm text-muted-foreground">Войдите, чтобы просматривать ленту активности.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-xl font-semibold text-foreground">Лента активности</h1>

      {/* Tab switcher */}
      <div className="mb-6 flex gap-1 rounded-xl bg-secondary p-1">
        {(["my", "following"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={[
              "flex-1 rounded-lg py-2 text-sm font-medium transition-all",
              tab === t
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            {t === "my" ? "Моя активность" : "Подписки"}
          </button>
        ))}
      </div>

      {/* Loading */}
      {isLoading && <FeedSkeleton />}

      {/* Error */}
      {isError && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-destructive/20 bg-destructive/5 p-8 text-center">
          <RefreshCw className="h-8 w-8 text-destructive/50" aria-hidden="true" strokeWidth={1.5} />
          <p className="text-sm text-destructive">Не удалось загрузить ленту активности.</p>
          <button
            onClick={() => isMyTab ? myActivity.refetch() : socialFeed.refetch()}
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted"
          >
            Попробовать снова
          </button>
        </div>
      )}

      {/* Empty — no following */}
      {!isLoading && !isError && !isMyTab && followedUserIds.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-border bg-card p-8 text-center">
          <Users className="h-10 w-10 text-muted-foreground/30" aria-hidden="true" strokeWidth={1.5} />
          <p className="text-sm text-muted-foreground">
            Подпишитесь на других участников, чтобы видеть их активность
          </p>
        </div>
      )}

      {/* Empty — no activity */}
      {!isLoading &&
        !isError &&
        activities.length === 0 &&
        (isMyTab || followedUserIds.length > 0) && (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-border bg-card p-8 text-center">
            <Activity
              className="h-10 w-10 text-muted-foreground/30"
              aria-hidden="true"
              strokeWidth={1.5}
            />
            <p className="text-sm text-muted-foreground">
              {isMyTab
                ? "Пока нет активности."
                : "Нет активности от пользователей, на которых вы подписаны."}
            </p>
          </div>
        )}

      {/* Activity list */}
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
