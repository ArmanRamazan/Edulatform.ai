"use client";

import { BlockErrorBoundary } from "./BlockErrorBoundary";
import { GreetingBlock } from "./blocks/GreetingBlock";
import { MissionBlock } from "./blocks/MissionBlock";
import { TrustLevelBlock } from "./blocks/TrustLevelBlock";
import { FlashcardsBlock } from "./blocks/FlashcardsBlock";
import { MasteryBlock } from "./blocks/MasteryBlock";
import { ActivityBlock } from "./blocks/ActivityBlock";
import { TeamProgressBlock } from "./blocks/TeamProgressBlock";

export function DashboardGrid() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      <BlockErrorBoundary fallbackTitle="Greeting failed">
        <GreetingBlock />
      </BlockErrorBoundary>

      <BlockErrorBoundary fallbackTitle="Mission failed">
        <MissionBlock />
      </BlockErrorBoundary>

      <BlockErrorBoundary fallbackTitle="Trust level failed">
        <TrustLevelBlock />
      </BlockErrorBoundary>

      <BlockErrorBoundary fallbackTitle="Flashcards failed">
        <FlashcardsBlock />
      </BlockErrorBoundary>

      <BlockErrorBoundary fallbackTitle="Mastery failed">
        <MasteryBlock />
      </BlockErrorBoundary>

      <BlockErrorBoundary fallbackTitle="Activity failed">
        <ActivityBlock />
      </BlockErrorBoundary>

      <BlockErrorBoundary fallbackTitle="Team progress failed">
        <TeamProgressBlock />
      </BlockErrorBoundary>
    </div>
  );
}
