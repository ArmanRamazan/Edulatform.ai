"use client";

import { AlertCircle } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { useDailySummary } from "@/hooks/use-daily";

const BLOCK_ANIMATION = {
  initial: { opacity: 0, scale: 0.97 },
  animate: { opacity: 1, scale: 1 },
  transition: { duration: 0.3 },
};

const LEVEL_NAMES: Record<number, string> = {
  0: "Newcomer",
  1: "Explorer",
  2: "Contributor",
  3: "Master",
  4: "Expert",
  5: "Mentor",
};

const MISSIONS_PER_LEVEL = 10;

function TrustRing({ progress, level }: { progress: number; level: number }) {
  const radius = 40;
  const stroke = 6;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progress / 100) * circumference;

  return (
    <svg width="100" height="100" viewBox="0 0 100 100" className="shrink-0">
      {/* Background ring */}
      <circle
        cx="50"
        cy="50"
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        className="text-muted"
      />
      {/* Progress ring */}
      <circle
        cx="50"
        cy="50"
        r={radius}
        fill="none"
        stroke="url(#trustGradient)"
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform="rotate(-90 50 50)"
        className="transition-all duration-700"
      />
      {/* Level number */}
      <text
        x="50"
        y="50"
        textAnchor="middle"
        dominantBaseline="central"
        className="fill-card-foreground font-mono text-2xl font-semibold"
        style={{ fontSize: "24px", fontWeight: 600 }}
      >
        {level}
      </text>
      <defs>
        <linearGradient id="trustGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="var(--primary)" />
          <stop offset="50%" stopColor="var(--chart-4)" />
          <stop offset="100%" stopColor="var(--success)" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export function TrustLevelBlock() {
  const { token } = useAuth();
  const { data: summary, isLoading, error, refetch } = useDailySummary(token);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-24" />
        </CardHeader>
        <CardContent className="flex items-center gap-4">
          <Skeleton className="size-[100px] rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-4 w-36" />
          </div>
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
          <p className="text-xs text-muted-foreground">Couldn&apos;t load your trust level.</p>
          <Button variant="outline" size="sm" className="mt-1" onClick={() => void refetch()}>
            Try again
          </Button>
        </CardContent>
      </Card>
    );
  }

  const { trust_level } = summary;
  const levelName = LEVEL_NAMES[trust_level.level] ?? `Level ${trust_level.level}`;
  const progressInLevel = trust_level.total_missions_completed % MISSIONS_PER_LEVEL;
  const progressPct = (progressInLevel / MISSIONS_PER_LEVEL) * 100;
  const missionsToNext = MISSIONS_PER_LEVEL - progressInLevel;

  return (
    <motion.div {...BLOCK_ANIMATION}>
      <Card>
        <CardHeader>
          <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Trust Level
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-4">
          <TrustRing progress={progressPct} level={trust_level.level} />
          <div>
            <h3 className="text-lg font-semibold text-card-foreground">
              {levelName}
            </h3>
            <p className="text-sm text-muted-foreground">
              <span className="font-mono">{progressInLevel}/{MISSIONS_PER_LEVEL}</span>{" "}
              missions to{" "}
              {LEVEL_NAMES[trust_level.level + 1] ?? "next level"}
            </p>
            <div className="mt-2 flex gap-3 text-xs text-muted-foreground">
              <span>
                <span className="font-mono font-semibold text-card-foreground">
                  {trust_level.total_missions_completed}
                </span>{" "}
                missions
              </span>
              <span>
                <span className="font-mono font-semibold text-card-foreground">
                  {trust_level.total_concepts_mastered}
                </span>{" "}
                concepts
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
