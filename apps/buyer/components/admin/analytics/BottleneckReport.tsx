"use client";

import Link from "next/link";
import { AlertTriangle, BookOpen, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/hooks/use-auth";
import { useActiveOrg } from "@/hooks/use-active-org";
import { useBottlenecks, type BottleneckItem } from "@/hooks/use-analytics";

// ---------- Severity ----------

function severityColor(pct: number): string {
  if (pct >= 80) return "text-red-400";
  if (pct >= 65) return "text-orange-400";
  return "text-yellow-400";
}

function severityBadge(pct: number): "destructive" | "secondary" {
  return pct >= 70 ? "destructive" : "secondary";
}

// ---------- Single bottleneck row ----------

interface BottleneckRowProps {
  item: BottleneckItem;
}

function BottleneckRow({ item }: BottleneckRowProps) {
  return (
    <div className="group flex items-start gap-4 rounded-lg border border-border/50 p-4 transition-colors hover:bg-secondary/50">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-destructive/10">
        <AlertTriangle className={`h-4 w-4 ${severityColor(item.stuck_percentage)}`} />
      </div>

      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-medium text-card-foreground">
            {item.concept_name}
          </h4>
          <Badge variant={severityBadge(item.stuck_percentage)} className="text-[10px]">
            {item.stuck_percentage}% stuck
          </Badge>
        </div>

        <Progress
          value={item.stuck_percentage}
          className="h-1.5"
        />

        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            {item.stuck_count} of {item.total_members} members need help
          </p>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1 text-xs text-primary opacity-0 transition-opacity group-hover:opacity-100">
              <BookOpen className="h-3 w-3" />
              Add documentation
            </span>
            <Link
              href={`/graph?concept=${item.concept_id}`}
              className="flex items-center gap-1 text-xs text-primary hover:underline"
            >
              View in graph
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------- Skeleton ----------

function BottleneckSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-4 w-40" />
      </CardHeader>
      <CardContent className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-start gap-4 rounded-lg border border-border/50 p-4">
            <Skeleton className="h-9 w-9 rounded-lg" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-1.5 w-full" />
              <Skeleton className="h-3 w-32" />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ---------- Main component ----------

export function BottleneckReport() {
  const { token } = useAuth();
  const { activeOrg } = useActiveOrg();
  const orgId = activeOrg?.id ?? null;

  const { data: bottlenecks, isLoading } = useBottlenecks(token, orgId);

  if (isLoading || !bottlenecks) {
    return <BottleneckSkeleton />;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Knowledge Bottlenecks
          </CardTitle>
          {bottlenecks.length > 0 && (
            <Badge variant="destructive" className="ml-2 text-[10px]">
              {bottlenecks.length} found
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {bottlenecks.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10">
              <BookOpen className="h-6 w-6 text-emerald-500" />
            </div>
            <p className="text-sm font-medium text-card-foreground">
              No bottlenecks detected
            </p>
            <p className="text-xs text-muted-foreground">
              All concepts have healthy coverage across the team.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {bottlenecks.map((item) => (
              <BottleneckRow key={item.concept_id} item={item} />
            ))}

            <div className="rounded-lg bg-primary/5 p-3">
              <p className="text-xs text-muted-foreground">
                <strong className="text-primary">Recommendation:</strong>{" "}
                Add more documentation, examples, or missions for the
                highlighted concepts to help your team bridge knowledge gaps.
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
