"use client";

import { use } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useDailySummary, useMissionHistory } from "@/hooks/use-daily";
import { MissionSession } from "@/components/mission/MissionSession";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
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
        <Card className="w-full max-w-md">
          <CardContent className="space-y-3 p-6">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-6">
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-sm text-muted-foreground">Please log in to start a mission.</p>
            <Button asChild className="mt-4">
              <Link href="/login">Log In</Link>
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
        <Card className="border-destructive/30">
          <CardContent className="p-6 text-center">
            <p className="text-sm text-destructive">Mission not found.</p>
            <Button variant="outline" asChild className="mt-4">
              <Link href="/dashboard">Back to Dashboard</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <MissionSession mission={mission} token={token} />;
}
