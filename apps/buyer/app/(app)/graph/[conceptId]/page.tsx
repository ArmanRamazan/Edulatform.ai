"use client";

import { use } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
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
  const { data: graph, isLoading: graphLoading, error: graphError } = useCourseGraph(
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
          <CardContent className="py-8 text-center">
            <p className="text-sm text-destructive">
              Missing courseId parameter. Navigate to a concept from the knowledge graph.
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
          <CardContent className="py-8 text-center">
            <p className="text-sm text-destructive">
              Failed to load concept data: {(graphError as Error)?.message ?? "Unknown error"}
            </p>
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
          <CardContent className="py-8 text-center">
            <p className="text-sm text-muted-foreground">
              Concept not found in the knowledge graph
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
