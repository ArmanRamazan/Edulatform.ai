"use client";

import Link from "next/link";
import { Users } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useMyGroups } from "@/hooks/use-study-groups";

function GroupsSkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading groups">
      {[1, 2, 3].map((i) => (
        <div key={i} className="relative overflow-hidden rounded-xl border border-border bg-card p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 space-y-2">
              <div className="relative h-5 w-48 overflow-hidden rounded bg-secondary">
                <div className="absolute inset-0 animate-shimmer" />
              </div>
              <div className="relative h-3 w-72 overflow-hidden rounded bg-secondary">
                <div className="absolute inset-0 animate-shimmer" />
              </div>
            </div>
            <div className="relative h-8 w-24 overflow-hidden rounded-lg bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function MyGroupsPage() {
  const { token, loading } = useAuth();
  const { data: groups, isLoading } = useMyGroups(token);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-6 text-2xl font-bold text-foreground">Мои учебные группы</h1>

      {/* Loading */}
      {(loading || isLoading) && <GroupsSkeleton />}

      {/* Empty */}
      {!loading && !isLoading && (!groups || groups.length === 0) && (
        <div className="flex flex-col items-center gap-4 rounded-2xl border border-border bg-card py-16 text-center">
          <Users
            className="h-12 w-12 text-muted-foreground/30"
            aria-hidden="true"
            strokeWidth={1.5}
          />
          <div>
            <p className="text-sm font-medium text-muted-foreground">
              Вы пока не состоите ни в одной учебной группе
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground/60">
              Группы появятся здесь после записи на курс
            </p>
          </div>
          <Link
            href="/dashboard"
            className="rounded-xl bg-primary/10 px-5 py-2 text-sm font-semibold text-primary ring-1 ring-primary/20 transition-all hover:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            На главную
          </Link>
        </div>
      )}

      {/* List */}
      {!loading && !isLoading && groups && groups.length > 0 && (
        <div className="space-y-2">
          {groups.map((group) => (
            <div
              key={group.id}
              className="rounded-xl border border-border bg-card p-4 transition-colors hover:border-border/60 hover:bg-muted/20"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <h2 className="font-medium text-foreground">{group.name}</h2>
                  {group.description && (
                    <p className="mt-1 text-sm text-muted-foreground">{group.description}</p>
                  )}
                  <p className="mt-1 text-xs text-muted-foreground/60">
                    Макс. участников: {group.max_members}
                  </p>
                </div>
                <Link
                  href={`/courses/${group.course_id}`}
                  className="shrink-0 rounded-lg border border-border bg-secondary px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:border-primary/30 hover:text-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  Открыть курс
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
