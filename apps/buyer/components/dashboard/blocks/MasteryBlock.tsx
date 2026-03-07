"use client";

import { AlertCircle, Brain } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { useAuth } from "@/hooks/use-auth";
import { useDailySummary } from "@/hooks/use-daily";

const BLOCK_ANIMATION = {
  initial: { opacity: 0, scale: 0.97 },
  animate: { opacity: 1, scale: 1 },
  transition: { duration: 0.3 },
};

function masteryColorClass(pct: number): string {
  if (pct >= 80) return "[&>div]:bg-success";
  if (pct >= 50) return "[&>div]:bg-info";
  if (pct >= 25) return "[&>div]:bg-primary";
  return "[&>div]:bg-muted-foreground";
}

export function MasteryBlock() {
  const { token } = useAuth();
  const { data: summary, isLoading, error, refetch } = useDailySummary(token);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-24" />
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="space-y-1">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-2 w-full" />
            </div>
          ))}
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
          <p className="text-xs text-muted-foreground">Couldn&apos;t load concept mastery data.</p>
          <Button variant="outline" size="sm" className="mt-1" onClick={() => void refetch()}>
            Try again
          </Button>
        </CardContent>
      </Card>
    );
  }

  const { trust_level } = summary;
  const totalMissions = trust_level.total_missions_completed;
  const totalConcepts = trust_level.total_concepts_mastered;
  const areas = trust_level.unlocked_areas;

  if (areas.length === 0 && totalMissions === 0) {
    return (
      <motion.div {...BLOCK_ANIMATION}>
        <Card>
          <CardHeader>
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Concept Mastery
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              icon={Brain}
              title="No mastery data yet"
              description="Complete missions to start tracking concept mastery."
              action={{ label: "View missions", href: "/dashboard" }}
            />
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  return (
    <motion.div {...BLOCK_ANIMATION}>
      <Card>
        <CardHeader>
          <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Concept Mastery
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4 grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-secondary p-3">
              <p className="font-mono text-xl font-semibold text-card-foreground">
                {totalMissions}
              </p>
              <p className="text-xs text-muted-foreground">missions done</p>
            </div>
            <div className="rounded-lg bg-secondary p-3">
              <p className="font-mono text-xl font-semibold text-card-foreground">
                {totalConcepts}
              </p>
              <p className="text-xs text-muted-foreground">concepts mastered</p>
            </div>
          </div>
          {areas.length > 0 && (
            <div className="space-y-2.5">
              <p className="text-xs text-muted-foreground">Unlocked areas</p>
              {areas.slice(0, 8).map((area, idx) => {
                const pct = Math.min(
                  100,
                  Math.round(((areas.length - idx) / areas.length) * 100),
                );
                return (
                  <div key={area} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-card-foreground">{area}</span>
                      <span className="font-mono text-muted-foreground">
                        {pct}%
                      </span>
                    </div>
                    <Progress
                      value={pct}
                      className={`h-2 ${masteryColorClass(pct)}`}
                    />
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
