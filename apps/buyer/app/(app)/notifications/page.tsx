"use client";

import { Bell, AlertCircle, RefreshCw } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useMyNotifications, useMarkRead } from "@/hooks/use-notifications";

const TYPE_LABELS: Record<string, string> = {
  registration: "Регистрация",
  enrollment: "Запись на курс",
  payment: "Оплата",
  mission: "Миссия",
  badge: "Достижение",
};

function NotificationSkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading notifications">
      <div className="relative h-4 w-24 overflow-hidden rounded bg-card border border-border">
        <div className="absolute inset-0 animate-shimmer" />
      </div>
      {[1, 2, 3].map((i) => (
        <div key={i} className="relative overflow-hidden rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-2">
            <div className="relative h-5 w-20 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
            <div className="relative h-4 w-52 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
          </div>
          <div className="relative mt-2 h-3 w-72 overflow-hidden rounded bg-secondary">
            <div className="absolute inset-0 animate-shimmer" />
          </div>
          <div className="relative mt-1 h-3 w-28 overflow-hidden rounded bg-secondary">
            <div className="absolute inset-0 animate-shimmer" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function NotificationsPage() {
  const { token, loading: authLoading } = useAuth();
  const { data, isLoading, isError, refetch } = useMyNotifications(token, { limit: 50 });
  const markRead = useMarkRead(token);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-6 text-xl font-semibold text-foreground">Уведомления</h1>

      {/* ── Loading ── */}
      {(authLoading || isLoading) && <NotificationSkeleton />}

      {/* ── Error ── */}
      {!isLoading && !authLoading && isError && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-destructive/20 bg-destructive/5 py-12 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <AlertCircle
              className="h-6 w-6 text-destructive"
              aria-hidden="true"
              strokeWidth={1.5}
            />
          </div>
          <div>
            <p className="text-sm font-medium text-destructive">
              Не удалось загрузить уведомления
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Проверьте подключение и попробуйте снова
            </p>
          </div>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            Повторить
          </button>
        </div>
      )}

      {/* ── Empty ── */}
      {!isLoading && !authLoading && !isError && (!data || data.items.length === 0) && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-border bg-card py-16 text-center">
          <Bell
            className="h-12 w-12 text-muted-foreground/30"
            aria-hidden="true"
            strokeWidth={1.5}
          />
          <p className="text-sm font-medium text-muted-foreground">Уведомлений пока нет</p>
          <p className="text-xs text-muted-foreground/60">
            Мы уведомим вас о важных событиях
          </p>
        </div>
      )}

      {/* ── List ── */}
      {!isLoading && !authLoading && !isError && data && data.items.length > 0 && (
        <>
          <p className="mb-3 text-sm text-muted-foreground">
            Всего:{" "}
            <span className="tabular-nums font-medium text-foreground">{data.total}</span>
          </p>
          <div className="space-y-2">
            {data.items.map((n) => (
              <div
                key={n.id}
                className={[
                  "group rounded-xl border p-4 transition-colors",
                  n.is_read
                    ? "border-border bg-card hover:bg-muted/20"
                    : "border-primary/20 bg-primary/5 hover:bg-primary/8",
                ].join(" ")}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
                    {/* Unread dot */}
                    {!n.is_read && (
                      <span
                        className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-primary"
                        aria-label="Непрочитано"
                      />
                    )}
                    <span className="rounded-md bg-secondary px-2 py-0.5 text-xs font-medium text-muted-foreground">
                      {TYPE_LABELS[n.type] ?? n.type}
                    </span>
                    <span className="text-sm font-medium text-foreground">{n.title}</span>
                  </div>
                  {!n.is_read && (
                    <button
                      onClick={() => markRead.mutate(n.id)}
                      disabled={markRead.isPending}
                      className="shrink-0 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
                    >
                      Прочитано
                    </button>
                  )}
                </div>
                {n.body && (
                  <p className="mt-1.5 text-sm text-muted-foreground">{n.body}</p>
                )}
                <p className="mt-1 text-xs text-muted-foreground/50">
                  {new Date(n.created_at).toLocaleString("ru")}
                </p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
