"use client";

import { useState } from "react";
import { AlertCircle, ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { useActiveOrg } from "@/hooks/use-active-org";
import { useConceptTeamMastery } from "@/hooks/use-concept-hub";

const STORAGE_KEY = "concept-hub-team-collapsed";

interface TeamMasteryBlockProps {
  conceptName: string;
  index: number;
}

export function TeamMasteryBlock({ conceptName, index }: TeamMasteryBlockProps) {
  const { token, user } = useAuth();
  const { activeOrg } = useActiveOrg();
  const isAdmin = user?.role === "admin" || user?.role === "teacher";

  const { data: members, isLoading, error, refetch } = useConceptTeamMastery(
    token,
    activeOrg?.id ?? null,
    isAdmin,
  );

  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(STORAGE_KEY) === "true";
  });

  function toggleCollapse() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(STORAGE_KEY, String(next));
  }

  // Hidden for non-admin users
  if (!isAdmin) {
    return null;
  }

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
              <Skeleton className="h-3 flex-1" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/30">
        <CardContent className="flex items-center justify-between gap-3 py-5">
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
            Failed to load team mastery
          </div>
          <Button size="sm" variant="ghost" className="h-7 gap-1.5 text-xs" onClick={() => refetch()}>
            <RefreshCw className="size-3" aria-hidden="true" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
    >
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Team Mastery - {conceptName}
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleCollapse}
            className="h-6 w-6 p-0"
            aria-label={collapsed ? "Expand Team Mastery" : "Collapse Team Mastery"}
            aria-expanded={!collapsed}
          >
            {collapsed ? <ChevronDown className="size-4" /> : <ChevronUp className="size-4" />}
          </Button>
        </CardHeader>
        {!collapsed && (
          <CardContent className="space-y-3">
            {!members || members.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No team members found
              </p>
            ) : (
              members.slice(0, 10).map((member) => {
                // Simulate mastery percentage based on member level (0-5 → 0-100%)
                const masteryPct = Math.min(100, Math.round((member.level / 5) * 100));
                const initials = member.user_id.slice(0, 2).toUpperCase();

                return (
                  <div key={member.user_id} className="flex items-center gap-3">
                    <Avatar className="size-8">
                      <AvatarFallback className="bg-primary/10 text-xs text-primary">
                        {initials}
                      </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex items-center justify-between text-xs">
                        <span className="truncate text-card-foreground">
                          {member.user_id.slice(0, 8)}
                        </span>
                        <span className="font-mono text-muted-foreground">
                          {masteryPct}%
                        </span>
                      </div>
                      <Progress
                        value={masteryPct}
                        className="h-1.5"
                      />
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        )}
      </Card>
    </motion.div>
  );
}
