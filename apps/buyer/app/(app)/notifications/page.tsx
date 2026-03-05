"use client";

import Link from "next/link";
import { Header } from "@/components/Header";
import { useAuth } from "@/hooks/use-auth";
import { useMyNotifications, useMarkRead } from "@/hooks/use-notifications";

const TYPE_LABELS: Record<string, string> = {
  registration: "Регистрация",
  enrollment: "Запись на курс",
  payment: "Оплата",
};

export default function NotificationsPage() {
  const { token, user, loading } = useAuth();
  const { data, isLoading } = useMyNotifications(token, { limit: 50 });
  const markRead = useMarkRead(token);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-4 py-6">
        <h1 className="mb-4 text-2xl font-bold">Уведомления</h1>

        {loading || isLoading ? (
          <p className="text-gray-400">Загрузка...</p>
        ) : !user ? (
          <p className="text-gray-500">
            <Link href="/login" className="text-blue-600 hover:underline">
              Войдите
            </Link>{" "}
            чтобы увидеть уведомления.
          </p>
        ) : !data || data.items.length === 0 ? (
          <p className="text-gray-500">Уведомлений пока нет.</p>
        ) : (
          <>
            <p className="mb-4 text-sm text-gray-400">Всего: {data.total}</p>
            <div className="space-y-3">
              {data.items.map((n) => (
                <div
                  key={n.id}
                  className={`rounded-lg border p-4 ${
                    n.is_read
                      ? "border-gray-200 bg-white"
                      : "border-blue-200 bg-blue-50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                        {TYPE_LABELS[n.type] || n.type}
                      </span>
                      <span className="ml-2 text-sm font-medium">{n.title}</span>
                    </div>
                    {!n.is_read && (
                      <button
                        onClick={() => markRead.mutate(n.id)}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Прочитано
                      </button>
                    )}
                  </div>
                  {n.body && <p className="mt-1 text-sm text-gray-500">{n.body}</p>}
                  <p className="mt-1 text-xs text-gray-400">
                    {new Date(n.created_at).toLocaleString("ru")}
                  </p>
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    </>
  );
}
