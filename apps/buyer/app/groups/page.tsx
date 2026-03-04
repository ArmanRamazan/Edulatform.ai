"use client";

import Link from "next/link";
import { Header } from "@/components/Header";
import { useAuth } from "@/hooks/use-auth";
import { useMyGroups } from "@/hooks/use-study-groups";

export default function MyGroupsPage() {
  const { token, user, loading } = useAuth();
  const { data: groups, isLoading } = useMyGroups(token);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-4 py-6">
        <h1 className="mb-6 text-2xl font-bold">Мои учебные группы</h1>

        {loading || isLoading ? (
          <p className="text-gray-400">Загрузка...</p>
        ) : !user ? (
          <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
            <p className="mb-4 text-gray-500">Войдите, чтобы увидеть свои группы</p>
            <Link
              href="/login"
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
            >
              Войти
            </Link>
          </div>
        ) : !groups || groups.length === 0 ? (
          <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
            <p className="mb-4 text-gray-500">Вы пока не состоите ни в одной учебной группе</p>
            <Link
              href="/"
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
            >
              Перейти к курсам
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {groups.map((group) => (
              <div
                key={group.id}
                className="rounded-lg border border-gray-200 bg-white p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <h2 className="font-medium text-gray-800">{group.name}</h2>
                    {group.description && (
                      <p className="mt-1 text-sm text-gray-500">{group.description}</p>
                    )}
                    <p className="mt-1 text-xs text-gray-400">
                      Макс. участников: {group.max_members}
                    </p>
                  </div>
                  <Link
                    href={`/courses/${group.course_id}`}
                    className="shrink-0 rounded border border-blue-200 px-3 py-1 text-sm text-blue-600 hover:bg-blue-50"
                  >
                    Открыть курс
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
