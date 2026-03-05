"use client";

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAuth } from "@/hooks/use-auth";
import { useActiveOrg } from "@/hooks/use-active-org";
import {
  useConceptCoverage,
  type ConceptCoverageData,
  type MasteryStatus,
} from "@/hooks/use-analytics";

// ---------- Color mapping ----------

const STATUS_COLORS: Record<MasteryStatus, string> = {
  mastered: "#34d399",
  learning: "#7c5cfc",
  not_started: "#3f3f46",
};

const STATUS_LABELS: Record<MasteryStatus, string> = {
  mastered: "Mastered",
  learning: "Learning",
  not_started: "Not Started",
};

// ---------- Heatmap cell ----------

interface HeatmapCellProps {
  status: MasteryStatus;
  conceptName: string;
  memberId: string;
}

function HeatmapCell({ status, conceptName, memberId }: HeatmapCellProps) {
  return (
    <TooltipTrigger asChild>
      <div
        className="h-7 w-7 shrink-0 rounded-sm transition-transform hover:scale-110"
        style={{ backgroundColor: STATUS_COLORS[status] }}
        aria-label={`${conceptName}: ${memberId} — ${STATUS_LABELS[status]}`}
      />
    </TooltipTrigger>
  );
}

// ---------- Heatmap grid ----------

interface HeatmapGridProps {
  coverage: ConceptCoverageData;
}

function HeatmapGrid({ coverage }: HeatmapGridProps) {
  const gapStats = useMemo(() => {
    return coverage.concepts.map((concept, ci) => {
      const row = coverage.matrix[ci];
      const weakCount = row.filter(
        (c) => c.status === "not_started" || c.status === "learning",
      ).length;
      const pct =
        coverage.members.length > 0
          ? Math.round((weakCount / coverage.members.length) * 100)
          : 0;
      return { concept, weakCount, pct, isGap: pct > 50 };
    });
  }, [coverage]);

  return (
    <TooltipProvider delayDuration={200}>
      <ScrollArea className="w-full">
        <div className="min-w-[600px]">
          {/* Column headers — member IDs */}
          <div className="mb-1 flex items-end gap-1 pl-40">
            {coverage.members.map((m) => (
              <div
                key={m.user_id}
                className="flex h-7 w-7 shrink-0 items-center justify-center"
                title={m.user_id}
              >
                <span className="text-[9px] font-mono text-muted-foreground">
                  {m.user_id.slice(0, 2)}
                </span>
              </div>
            ))}
          </div>

          {/* Rows — concepts */}
          {gapStats.map(({ concept, pct, isGap }, ci) => (
            <div key={concept.id} className="flex items-center gap-1 py-0.5">
              {/* Row label */}
              <div className="flex w-40 shrink-0 items-center gap-2">
                <span
                  className={`truncate text-xs ${isGap ? "font-semibold text-red-400" : "text-muted-foreground"}`}
                  title={concept.name}
                >
                  {concept.name}
                </span>
                {isGap && (
                  <Badge
                    variant="destructive"
                    className="shrink-0 text-[10px] px-1 py-0"
                  >
                    {pct}%
                  </Badge>
                )}
              </div>

              {/* Cells */}
              {coverage.matrix[ci].map((cell, mi) => (
                <Tooltip key={`${ci}-${mi}`}>
                  <HeatmapCell
                    status={cell.status}
                    conceptName={concept.name}
                    memberId={coverage.members[mi].user_id}
                  />
                  <TooltipContent
                    side="top"
                    className="bg-popover text-popover-foreground"
                  >
                    <p className="text-xs font-medium">{concept.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {coverage.members[mi].user_id.slice(0, 8)}...
                    </p>
                    <p className="text-xs" style={{ color: STATUS_COLORS[cell.status] }}>
                      {STATUS_LABELS[cell.status]}
                    </p>
                  </TooltipContent>
                </Tooltip>
              ))}
            </div>
          ))}
        </div>
      </ScrollArea>
    </TooltipProvider>
  );
}

// ---------- Legend ----------

function HeatmapLegend() {
  return (
    <div className="flex items-center gap-4 text-xs text-muted-foreground print:text-black">
      {(Object.entries(STATUS_COLORS) as [MasteryStatus, string][]).map(
        ([status, color]) => (
          <div key={status} className="flex items-center gap-1.5">
            <div
              className="h-3 w-3 rounded-sm"
              style={{ backgroundColor: color }}
            />
            <span>{STATUS_LABELS[status]}</span>
          </div>
        ),
      )}
    </div>
  );
}

// ---------- Skeleton ----------

function CoverageSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-4 w-48" />
      </CardHeader>
      <CardContent className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center gap-2">
            <Skeleton className="h-4 w-32" />
            <div className="flex gap-1">
              {Array.from({ length: 8 }).map((_, j) => (
                <Skeleton key={j} className="h-7 w-7 rounded-sm" />
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ---------- Main component ----------

export function ConceptCoverage() {
  const { token } = useAuth();
  const { activeOrg } = useActiveOrg();
  const orgId = activeOrg?.id ?? null;

  const { data: coverage, isLoading } = useConceptCoverage(token, orgId);

  if (isLoading || !coverage) {
    return <CoverageSkeleton />;
  }

  if (coverage.members.length === 0 || coverage.concepts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Concept Coverage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="py-8 text-center text-sm text-muted-foreground">
            No data available yet. Team members need to start missions.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Concept Coverage Heatmap
        </CardTitle>
        <HeatmapLegend />
      </CardHeader>
      <CardContent>
        <HeatmapGrid coverage={coverage} />
        <p className="mt-3 text-xs text-muted-foreground">
          Red-highlighted concepts indicate knowledge gaps where &gt;50% of the team has not mastered the material.
        </p>
      </CardContent>
    </Card>
  );
}
