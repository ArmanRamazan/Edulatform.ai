"use client";

import Link from "next/link";
import {
  Activity,
  BookOpen,
  Brain,
  Award,
  Flame,
  CheckCircle,
  type LucideIcon,
} from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { useAuth } from "@/hooks/use-auth";
import { useMyActivity } from "@/hooks/use-activity";

const BLOCK_ANIMATION = {
  initial: { opacity: 0, scale: 0.97 },
  animate: { opacity: 1, scale: 1 },
  transition: { duration: 0.3 },
};

const ACTIVITY_ICONS: Record<string, LucideIcon> = {
  quiz_completed: BookOpen,
  flashcard_reviewed: Brain,
  badge_earned: Award,
  streak_milestone: Flame,
  concept_mastered: CheckCircle,
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
  const { data, isLoading, error } = useMyActivity(token, { limit: 5 });

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
      <Card className="border-destructive/30">
        <CardContent className="py-5 text-sm text-destructive">
          Failed to load activity
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
            <EmptyState
              icon={Activity}
              title="No recent activity"
              description="Complete a mission or review flashcards to see activity here."
              action={{ label: "Review flashcards", href: "/flashcards" }}
            />
          ) : (
            <ul className="space-y-3">
              {activities.map((a) => {
                const Icon = ACTIVITY_ICONS[a.activity_type] ?? CheckCircle;
                return (
                  <li key={a.id} className="flex items-center gap-3">
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-secondary">
                      <Icon className="size-4 text-muted-foreground" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-card-foreground">
                        {activityDescription(a.activity_type)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {relativeTime(a.created_at)}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
