"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldAlert, CheckCircle2 } from "lucide-react";
import { admin } from "@/lib/api";
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
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-center">
        <ShieldAlert
          className="h-10 w-10 text-destructive/50"
          aria-hidden="true"
          strokeWidth={1.5}
        />
        <p className="text-sm font-medium text-muted-foreground">Доступ запрещён</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-4 text-2xl font-bold text-foreground">Верификация преподавателей</h1>

      {/* Loading */}
      {isLoading && (
        <div className="space-y-2" aria-busy="true">
          {[1, 2, 3].map((i) => (
            <div key={i} className="relative h-14 overflow-hidden rounded-xl border border-border bg-card">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
          ))}
        </div>
      )}

      {/* Empty */}
      {!isLoading && (!data || data.items.length === 0) && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-border bg-card py-16 text-center">
          <CheckCircle2
            className="h-10 w-10 text-success/50"
            aria-hidden="true"
            strokeWidth={1.5}
          />
          <p className="text-sm text-muted-foreground">Нет заявок на верификацию</p>
        </div>
      )}

      {/* Table */}
      {!isLoading && data && data.items.length > 0 && (
        <>
          <p className="mb-4 text-sm text-muted-foreground">
            Всего заявок:{" "}
            <span className="tabular-nums font-medium text-foreground">{data.total}</span>
          </p>
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-secondary/50">
                <tr>
                  <th className="px-4 py-3 font-medium text-muted-foreground">Имя</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground">Email</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground">Дата регистрации</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground"></th>
                </tr>
              </thead>
              <tbody className="bg-card">
                {data.items.map((t) => (
                  <tr
                    key={t.id}
                    className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-foreground">{t.name}</td>
                    <td className="px-4 py-3 text-muted-foreground">{t.email}</td>
                    <td className="px-4 py-3 text-muted-foreground/60">
                      {new Date(t.created_at).toLocaleDateString("ru")}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => verify.mutate(t.id)}
                        disabled={verify.isPending}
                        className="rounded-lg bg-success/15 px-3 py-1.5 text-xs font-semibold text-success ring-1 ring-success/20 transition-all hover:bg-success/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
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
    </div>
  );
}
