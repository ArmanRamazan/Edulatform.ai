"use client";

import { Flame } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
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
  const { data: summary, isLoading, error } = useDailySummary(token);

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
      <Card className="border-destructive/30">
        <CardContent className="py-5 text-sm text-destructive">
          Failed to load greeting
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
            <Flame className="size-5 text-orange-500" />
            <span className="font-mono text-2xl font-bold text-card-foreground">
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
