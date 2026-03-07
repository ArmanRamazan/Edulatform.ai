"use client";

import { AlertCircle, Flame } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { useDailySummary } from "@/hooks/use-daily";

const BLOCK_ANIMATION = {
  initial: { opacity: 0, scale: 0.97 },
  animate: { opacity: 1, scale: 1 },
  transition: { duration: 0.3 },
};

export function GreetingBlock() {
  const { token } = useAuth();
  const { data: summary, isLoading, error, refetch } = useDailySummary(token);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="space-y-3 py-5">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
        </CardContent>
      </Card>
    );
  }

  if (error || !summary) {
    return (
      <Card className="border-destructive/30 bg-destructive/5" role="alert">
        <CardContent className="flex flex-col items-center justify-center gap-2 py-8 text-center">
          <AlertCircle className="h-5 w-5 text-destructive" aria-hidden="true" strokeWidth={1.5} />
          <p className="text-sm font-medium text-destructive">Something went wrong</p>
          <p className="text-xs text-muted-foreground">Couldn&apos;t load your greeting. Please try again.</p>
          <Button variant="outline" size="sm" className="mt-1" onClick={() => void refetch()}>
            Try again
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div {...BLOCK_ANIMATION}>
      <Card>
        <CardContent className="py-5">
          <p className="mb-2 text-lg font-semibold text-card-foreground">
            {summary.greeting}
          </p>
          <div className="flex items-center gap-2">
            <Flame className="size-5 text-warning" />
            <span className="font-mono text-2xl font-semibold text-warning">
              {summary.streak_days}
            </span>
            <span className="text-sm text-muted-foreground">
              {dayWord(summary.streak_days)} streak
            </span>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function dayWord(n: number): string {
  if (n === 1) return "day";
  return "days";
}
