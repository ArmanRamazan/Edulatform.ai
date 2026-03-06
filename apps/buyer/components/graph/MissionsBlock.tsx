"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp, Zap, CheckCircle2 } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { useConceptMissions } from "@/hooks/use-concept-hub";

const STORAGE_KEY = "concept-hub-missions-collapsed";

interface MissionsBlockProps {
  conceptId: string;
  index: number;
}

export function MissionsBlock({ conceptId, index }: MissionsBlockProps) {
  const { token } = useAuth();
  const { data: missions, isLoading, error } = useConceptMissions(token, conceptId);

  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(STORAGE_KEY) === "true";
  });

  function toggleCollapse() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(STORAGE_KEY, String(next));
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-28" />
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/30">
        <CardContent className="py-5 text-sm text-destructive">
          Failed to load missions
        </CardContent>
      </Card>
    );
  }

  const completed = missions?.filter((m) => m.status === "completed") ?? [];
  const available = missions?.filter((m) => m.status !== "completed") ?? [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
    >
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Missions
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={toggleCollapse} className="h-6 w-6 p-0">
            {collapsed ? <ChevronDown className="size-4" /> : <ChevronUp className="size-4" />}
          </Button>
        </CardHeader>
        {!collapsed && (
          <CardContent className="space-y-3">
            {completed.length === 0 && available.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No missions yet for this concept
              </p>
            ) : (
              <>
                {/* Completed missions */}
                {completed.map((m) => (
                  <div
                    key={m.id}
                    className="flex items-center gap-3 rounded-lg border border-border p-3"
                  >
                    <CheckCircle2 className="size-5 shrink-0 text-emerald-500" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-card-foreground">
                        {m.blueprint?.concept_name ?? "Mission"}
                      </p>
                      {m.completed_at && (
                        <p className="text-xs text-muted-foreground">
                          {new Date(m.completed_at).toLocaleDateString("en", {
                            month: "short",
                            day: "numeric",
                          })}
                        </p>
                      )}
                    </div>
                    {m.score !== null && (
                      <Badge variant="secondary" className="font-mono">
                        {m.score}%
                      </Badge>
                    )}
                  </div>
                ))}

                {/* Available missions */}
                {available.map((m) => (
                  <div
                    key={m.id}
                    className="flex items-center gap-3 rounded-lg border border-border p-3"
                  >
                    <Zap className="size-5 shrink-0 text-primary" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-card-foreground">
                        {m.blueprint?.concept_name ?? "Mission"}
                      </p>
                      <Badge variant="outline" className="mt-1 text-[10px]">
                        {m.mission_type}
                      </Badge>
                    </div>
                    <Link href={`/missions/${m.id}`}>
                      <Button size="sm" variant="default" className="h-7 text-xs">
                        Start
                      </Button>
                    </Link>
                  </div>
                ))}
              </>
            )}
          </CardContent>
        )}
      </Card>
    </motion.div>
  );
}
