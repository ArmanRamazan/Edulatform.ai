"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { admin } from "@/lib/api";
import { Header } from "@/components/Header";
import { useAuth } from "@/hooks/use-auth";

export default function AdminTeachersPage() {
  const { user, token, loading } = useAuth();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "pendingTeachers"],
    queryFn: () => admin.pendingTeachers(token!),
    enabled: !!token && user?.role === "admin",
  });

  const verify = useMutation({
    mutationFn: (userId: string) => admin.verifyTeacher(token!, userId),
    onSuccess: (_data, userId) => {
      queryClient.setQueryData(
        ["admin", "pendingTeachers"],
        (old: typeof data | undefined) =>
          old
            ? { items: old.items.filter((t) => t.id !== userId), total: old.total - 1 }
            : undefined,
      );
    },
  });

  if (!loading && (!user || user.role !== "admin")) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-sm px-4 py-12 text-center">
          <p className="text-gray-500">Доступ запрещён</p>
        </main>
      </>
    );
  }

  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-4 py-6">
        <h1 className="mb-4 text-2xl font-bold">Верификация преподавателей</h1>

        {isLoading ? (
          <p className="text-gray-400">Загрузка...</p>
        ) : !data || data.items.length === 0 ? (
          <p className="text-gray-500">Нет заявок на верификацию</p>
        ) : (
          <>
            <p className="mb-4 text-sm text-gray-500">Всего заявок: {data.total}</p>
            <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-gray-200 bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 font-medium text-gray-600">Имя</th>
                    <th className="px-4 py-3 font-medium text-gray-600">Email</th>
                    <th className="px-4 py-3 font-medium text-gray-600">Дата регистрации</th>
                    <th className="px-4 py-3 font-medium text-gray-600"></th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((t) => (
                    <tr key={t.id} className="border-b border-gray-100 last:border-0">
                      <td className="px-4 py-3">{t.name}</td>
                      <td className="px-4 py-3 text-gray-500">{t.email}</td>
                      <td className="px-4 py-3 text-gray-400">
                        {new Date(t.created_at).toLocaleDateString("ru")}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => verify.mutate(t.id)}
                          disabled={verify.isPending}
                          className="rounded bg-green-600 px-3 py-1 text-xs text-white hover:bg-green-700 disabled:opacity-50"
                        >
                          {verify.isPending ? "..." : "Одобрить"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </main>
    </>
  );
}
