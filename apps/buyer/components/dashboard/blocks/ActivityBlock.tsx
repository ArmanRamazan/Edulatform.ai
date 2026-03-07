"use client";

import Link from "next/link";
import {
  Activity,
  AlertCircle,
  BookOpen,
  Brain,
  Award,
  Flame,
  CheckCircle,
  type LucideIcon,
} from "lucide-react";
import { motion } from "framer-motion";
import type { Variants } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { useMyActivity } from "@/hooks/use-activity";

const BLOCK_ANIMATION = {
  initial: { opacity: 0, scale: 0.97 },
  animate: { opacity: 1, scale: 1 },
  transition: { duration: 0.3 },
};

const LIST_VARIANTS: Variants = {
  animate: { transition: { staggerChildren: 0.055 } },
};

const ITEM_VARIANTS: Variants = {
  initial: { opacity: 0, x: -8 },
  animate: { opacity: 1, x: 0, transition: { duration: 0.22, ease: [0.25, 0, 0, 1] } },
};

const ACTIVITY_ICONS: Record<string, LucideIcon> = {
  quiz_completed: BookOpen,
  flashcard_reviewed: Brain,
  badge_earned: Award,
  streak_milestone: Flame,
  concept_mastered: CheckCircle,
};

// Semantic icon+bg color per activity type — aligned to design token palette
const ACTIVITY_COLORS: Record<string, { icon: string; bg: string }> = {
  quiz_completed:    { icon: "text-info",    bg: "bg-info/10" },
  flashcard_reviewed:{ icon: "text-primary", bg: "bg-primary/10" },
  badge_earned:      { icon: "text-warning", bg: "bg-warning/10" },
  streak_milestone:  { icon: "text-warning", bg: "bg-warning/10" },
  concept_mastered:  { icon: "text-success", bg: "bg-success/10" },
};

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function activityDescription(type: string): string {
  switch (type) {
    case "quiz_completed":
      return "Completed a quiz";
    case "flashcard_reviewed":
      return "Reviewed flashcards";
    case "badge_earned":
      return "Earned a badge";
    case "streak_milestone":
      return "Streak milestone";
    case "concept_mastered":
      return "Mastered a concept";
    default:
      return "Activity";
  }
}

export function ActivityBlock() {
  const { token } = useAuth();
  const { data, isLoading, error, refetch } = useMyActivity(token, { limit: 5 });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-28" />
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="size-8 rounded-full" />
              <div className="flex-1 space-y-1">
                <Skeleton className="h-3 w-32" />
                <Skeleton className="h-2 w-16" />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/30 bg-destructive/5" role="alert">
        <CardContent className="flex flex-col items-center justify-center gap-2 py-8 text-center">
          <AlertCircle className="h-5 w-5 text-destructive" aria-hidden="true" strokeWidth={1.5} />
          <p className="text-sm font-medium text-destructive">Something went wrong</p>
          <p className="text-xs text-muted-foreground">Couldn&apos;t load recent activity.</p>
          <Button variant="outline" size="sm" className="mt-1" onClick={() => void refetch()}>
            Try again
          </Button>
        </CardContent>
      </Card>
    );
  }

  const activities = data?.items ?? [];

  return (
    <motion.div {...BLOCK_ANIMATION}>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Recent Activity
            </CardTitle>
            {activities.length > 0 && (
              <Link
                href="/feed"
                className="text-xs text-primary hover:underline"
              >
                View all
              </Link>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {activities.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <div className="flex size-10 items-center justify-center rounded-full bg-secondary">
                <Activity className="size-4 text-muted-foreground" />
              </div>
              <p className="text-sm text-muted-foreground">No recent activity</p>
              <p className="text-xs text-muted-foreground/60">
                Complete a quiz or review flashcards to see events here
              </p>
            </div>
          ) : (
            <motion.ul
              className="space-y-2.5"
              variants={LIST_VARIANTS}
              initial="initial"
              animate="animate"
            >
              {activities.map((a) => {
                const Icon = ACTIVITY_ICONS[a.activity_type] ?? CheckCircle;
                const colors = ACTIVITY_COLORS[a.activity_type] ?? { icon: "text-muted-foreground", bg: "bg-secondary" };
                return (
                  <motion.li
                    key={a.id}
                    variants={ITEM_VARIANTS}
                    className="flex items-center gap-3 rounded-lg px-1 py-1 transition-colors hover:bg-secondary/50"
                  >
                    <div className={`flex size-8 shrink-0 items-center justify-center rounded-full ${colors.bg}`}>
                      <Icon className={`size-4 ${colors.icon}`} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-card-foreground">
                        {activityDescription(a.activity_type)}
                      </p>
                      <p className="font-mono text-xs text-muted-foreground">
                        {relativeTime(a.created_at)}
                      </p>
                    </div>
                  </motion.li>
                );
              })}
            </motion.ul>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
