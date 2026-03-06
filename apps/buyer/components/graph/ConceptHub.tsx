"use client";

import type { ConceptData, MasteryItem } from "@/lib/api";
import { BlockErrorBoundary } from "@/components/dashboard/BlockErrorBoundary";
import { ConceptHeader } from "./ConceptHeader";
import { InternalSourcesBlock } from "./InternalSourcesBlock";
import { MissionsBlock } from "./MissionsBlock";
import { TeamMasteryBlock } from "./TeamMasteryBlock";
import { DiscussionsBlock } from "./DiscussionsBlock";
import { RelatedGraphBlock } from "./RelatedGraphBlock";

interface ConceptHubProps {
  concept: ConceptData;
  allConcepts: ConceptData[];
  masteryItems: MasteryItem[];
}

export function ConceptHub({ concept, allConcepts, masteryItems }: ConceptHubProps) {
  const masteryItem = masteryItems.find((m) => m.concept_id === concept.id);
  const mastery = masteryItem ? Math.round(masteryItem.mastery * 100) : 0;

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <BlockErrorBoundary fallbackTitle="Header failed">
        <ConceptHeader
          concept={concept}
          allConcepts={allConcepts}
          mastery={mastery}
          index={0}
        />
      </BlockErrorBoundary>

      <BlockErrorBoundary fallbackTitle="Internal sources failed">
        <InternalSourcesBlock conceptName={concept.name} index={1} />
      </BlockErrorBoundary>

      <BlockErrorBoundary fallbackTitle="Missions failed">
        <MissionsBlock conceptId={concept.id} index={2} />
      </BlockErrorBoundary>

      <BlockErrorBoundary fallbackTitle="Team mastery failed">
        <TeamMasteryBlock conceptName={concept.name} index={3} />
      </BlockErrorBoundary>

      <BlockErrorBoundary fallbackTitle="Discussions failed">
        <DiscussionsBlock
          conceptId={concept.id}
          conceptName={concept.name}
          index={4}
        />
      </BlockErrorBoundary>

      <BlockErrorBoundary fallbackTitle="Related graph failed">
        <RelatedGraphBlock
          concept={concept}
          allConcepts={allConcepts}
          index={5}
        />
      </BlockErrorBoundary>
    </div>
  );
}
