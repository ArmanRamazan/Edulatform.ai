"use client";

import { useQuery } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { EmptyState } from "@/components/ui/EmptyState";
import { useAuth } from "@/hooks/use-auth";
import { useActiveOrg } from "@/hooks/use-active-org";
import { trustLevels } from "@/lib/api";

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

// Semantic badge color per trust level
const LEVEL_BADGE_CLASS: Record<number, string> = {
  0: "bg-secondary text-muted-foreground",
  1: "bg-info/10 text-info",
  2: "bg-primary/10 text-primary",
  3: "bg-warning/10 text-warning",
  4: "bg-success/10 text-success",
  5: "bg-gradient-to-r from-primary/20 to-success/20 text-primary",
};

export function TeamProgressBlock() {
  const { token, user } = useAuth();
  const { activeOrg } = useActiveOrg();

  const isAdmin = user?.role === "admin" || user?.role === "teacher";
  const orgId = activeOrg?.id ?? null;

  const { data: teamLevels, isLoading } = useQuery({
    queryKey: ["trust-levels", "org", orgId],
    queryFn: () => trustLevels.getOrgLevels(token!, orgId!, { limit: 10 }),
    enabled: !!token && !!orgId && isAdmin,
  });

  if (!isAdmin) return null;

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="size-8 rounded-full" />
              <Skeleton className="h-4 w-32" />
              <Skeleton className="ml-auto h-5 w-20" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (!orgId) return null;

  const levels = teamLevels?.levels ?? [];

  return (
    <motion.div {...BLOCK_ANIMATION}>
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Users className="size-4 text-muted-foreground" />
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Team Progress
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {levels.length === 0 ? (
            <EmptyState
              icon={Users}
              title="No team members yet"
              description="Invite engineers to your organization to track team progress."
            />
          ) : (
            <div className="space-y-3">
              {levels.map((member) => (
                <div
                  key={member.user_id}
                  className="flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors hover:bg-secondary"
                >
                  <Avatar className="size-8">
                    <AvatarFallback className="bg-primary/10 text-xs text-primary">
                      {member.user_id.slice(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-card-foreground">
                      {member.user_id.slice(0, 8)}...
                    </p>
                    <p className="text-xs text-muted-foreground">
                      <span className="font-mono">
                        {member.total_missions_completed}
                      </span>{" "}
                      missions
                    </p>
                  </div>
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium font-mono ${
                      LEVEL_BADGE_CLASS[member.level] ?? "bg-secondary text-muted-foreground"
                    }`}
                  >
                    {LEVEL_NAMES[member.level] ?? `Lvl ${member.level}`}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
