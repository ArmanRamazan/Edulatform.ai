"use client";

import { motion, useSpring, useTransform } from "framer-motion";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { useDailySummary, useStartMission } from "@/hooks/use-daily";

const BLOCK_ANIMATION = {
  initial: { opacity: 0, scale: 0.97 },
  animate: { opacity: 1, scale: 1 },
  transition: { duration: 0.3 },
};

function AnimatedScore({ value }: { value: number }) {
  const spring = useSpring(0, { stiffness: 50, damping: 20 });
  const display = useTransform(spring, (v) => Math.round(v));
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    spring.set(value);
    const unsubscribe = display.on("change", (v) => setCurrent(v));
    return unsubscribe;
  }, [value, spring, display]);

  return (
    <span className="font-mono text-3xl font-bold text-success">
      {current}%
    </span>
  );
}

function missionTypeBadge(missionType: string): {
  label: string;
  variant: "default" | "secondary" | "outline";
} {
  switch (missionType) {
    case "deep_dive":
      return { label: "Deep Dive", variant: "default" };
    case "practice":
      return { label: "Practice", variant: "secondary" };
    case "review":
      return { label: "Review", variant: "outline" };
    default:
      return { label: missionType, variant: "outline" };
  }
}

export function MissionBlock() {
  const { token } = useAuth();
  const { data: summary, isLoading, error } = useDailySummary(token);
  const startMission = useStartMission(token);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-24" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-9 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !summary) {
    return (
      <Card className="border-destructive/30">
        <CardContent className="py-5 text-sm text-destructive">
          Failed to load mission
        </CardContent>
      </Card>
    );
  }

  const { mission } = summary;

  if (!mission) {
    return (
      <motion.div {...BLOCK_ANIMATION}>
        <Card className="border-dashed border-muted-foreground/20">
          <CardContent className="flex flex-col items-center justify-center py-8 text-center">
            <p className="text-sm font-medium text-muted-foreground">
              No missions today
            </p>
            <p className="mt-1 text-xs text-muted-foreground/60">
              Rest up or review flashcards
            </p>
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  const conceptName = mission.blueprint?.concept_name ?? "Mission";
  const typeBadge = missionTypeBadge(mission.mission_type);

  return (
    <motion.div {...BLOCK_ANIMATION}>
      <Card className="relative overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-primary via-chart-4 to-success" />
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Today&apos;s Mission
            </CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant={typeBadge.variant}>{typeBadge.label}</Badge>
              <Badge
                variant={
                  mission.status === "completed"
                    ? "default"
                    : mission.status === "in_progress"
                      ? "secondary"
                      : "outline"
                }
              >
                {mission.status === "pending" && "Pending"}
                {mission.status === "in_progress" && "In Progress"}
                {mission.status === "completed" && "Completed"}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <h3 className="text-lg font-semibold text-card-foreground">
            {conceptName}
          </h3>

          {mission.status === "pending" && (
            <Button
              className="w-full shadow-[0_0_20px_rgba(124,92,252,0.3)] hover:shadow-[0_0_30px_rgba(124,92,252,0.5)]"
              onClick={() => startMission.mutate(mission.id)}
              disabled={startMission.isPending}
            >
              {startMission.isPending ? "Starting..." : "Start Mission"}
            </Button>
          )}

          {mission.status === "in_progress" && (
            <Button className="w-full" variant="secondary">
              Continue
            </Button>
          )}

          {mission.status === "completed" && mission.score !== null && (
            <div className="flex items-center justify-between rounded-lg bg-success/10 px-4 py-3">
              <span className="text-sm text-success">Score</span>
              <AnimatedScore value={mission.score} />
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
