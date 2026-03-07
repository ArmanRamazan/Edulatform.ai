"use client";

import { use } from "react";
import { useSearchParams } from "next/navigation";
import { AlertCircle, Network, RefreshCw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { useCourseGraph, useCourseMastery } from "@/hooks/use-concepts";
import { ConceptHub } from "@/components/graph/ConceptHub";

interface ConceptPageProps {
  params: Promise<{ conceptId: string }>;
}

export default function ConceptHubPage({ params }: ConceptPageProps) {
  const { conceptId } = use(params);
  const searchParams = useSearchParams();
  const courseId = searchParams.get("courseId") ?? "";

  const { token, loading: authLoading } = useAuth();
  const { data: graph, isLoading: graphLoading, error: graphError, refetch: refetchGraph } = useCourseGraph(
    token,
    courseId,
  );
  const { data: mastery, isLoading: masteryLoading } = useCourseMastery(
    token,
    courseId,
  );

  if (authLoading || graphLoading || masteryLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <Card>
          <CardContent className="space-y-4 py-6">
            <Skeleton className="h-3 w-32" />
            <div className="flex items-start gap-6">
              <Skeleton className="size-32 rounded-full" />
              <div className="flex-1 space-y-3">
                <Skeleton className="h-7 w-48" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            </div>
          </CardContent>
        </Card>
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="space-y-3 py-5">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-16 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!courseId) {
    return (
      <div className="mx-auto max-w-3xl">
        <Card className="border-destructive/30">
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <AlertCircle className="size-8 text-destructive" aria-hidden="true" />
            <p className="text-sm font-medium text-foreground">Missing course context</p>
            <p className="text-xs text-muted-foreground">
              Navigate to a concept from the knowledge graph to open its hub.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (graphError || !graph) {
    return (
      <div className="mx-auto max-w-3xl">
        <Card className="border-destructive/30">
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <AlertCircle className="size-8 text-destructive" aria-hidden="true" />
            <p className="text-sm font-medium text-foreground">Something went wrong</p>
            <p className="text-xs text-muted-foreground">
              Failed to load the knowledge graph. Check your connection and try again.
            </p>
            <Button
              size="sm"
              variant="outline"
              className="mt-1 gap-1.5"
              onClick={() => refetchGraph()}
            >
              <RefreshCw className="size-3.5" aria-hidden="true" />
              Try again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const concept = graph.concepts.find((c) => c.id === conceptId);
  if (!concept) {
    return (
      <div className="mx-auto max-w-3xl">
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <Network className="size-8 text-muted-foreground/40" aria-hidden="true" />
            <p className="text-sm font-medium text-foreground">Concept not found</p>
            <p className="text-xs text-muted-foreground">
              This concept doesn&apos;t exist in the knowledge graph for this course.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <ConceptHub
      concept={concept}
      allConcepts={graph.concepts}
      masteryItems={mastery?.items ?? []}
    />
  );
}
