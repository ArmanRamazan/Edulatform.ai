"use client";

import { use } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useDailySummary, useMissionHistory } from "@/hooks/use-daily";
import { MissionSession } from "@/components/mission/MissionSession";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, LogIn } from "lucide-react";
import Link from "next/link";

export default function MissionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { token, loading: authLoading } = useAuth();
  const { data: summary, isLoading: summaryLoading } = useDailySummary(token);
  const { data: history, isLoading: historyLoading } = useMissionHistory(token, 20);

  if (authLoading || summaryLoading || historyLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-6">
        <Card
          className="w-full max-w-md"
          aria-busy="true"
          aria-label="Loading mission"
        >
          <CardContent className="space-y-3 p-6">
            <div className="relative h-6 w-48 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
            <div className="relative h-4 w-full overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
            <div className="relative h-4 w-3/4 overflow-hidden rounded bg-secondary">
              <div className="absolute inset-0 animate-shimmer" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-6">
        <Card>
          <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <LogIn
                className="h-6 w-6 text-primary"
                aria-hidden="true"
                strokeWidth={1.5}
              />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">
                Требуется вход
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Войдите в аккаунт, чтобы начать миссию.
              </p>
            </div>
            <Button asChild className="mt-1">
              <Link href="/login">Войти</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const mission =
    summary?.mission?.id === id
      ? summary.mission
      : history?.items.find((m) => m.id === id);

  if (!mission) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-6">
        <Card className="border-destructive/20 bg-destructive/5" role="alert">
          <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
              <AlertCircle
                className="h-6 w-6 text-destructive"
                aria-hidden="true"
                strokeWidth={1.5}
              />
            </div>
            <div>
              <p className="text-sm font-medium text-destructive">
                Миссия не найдена
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Эта миссия недоступна или была удалена.
              </p>
            </div>
            <Button variant="outline" asChild className="mt-1">
              <Link href="/dashboard">На главную</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <MissionSession mission={mission} token={token} />;
}
