"use client";

import { motion } from "framer-motion";
import type { Variants } from "framer-motion";
import { BlockErrorBoundary } from "./BlockErrorBoundary";
import { GreetingBlock } from "./blocks/GreetingBlock";
import { MissionBlock } from "./blocks/MissionBlock";
import { TrustLevelBlock } from "./blocks/TrustLevelBlock";
import { FlashcardsBlock } from "./blocks/FlashcardsBlock";
import { MasteryBlock } from "./blocks/MasteryBlock";
import { ActivityBlock } from "./blocks/ActivityBlock";
import { TeamProgressBlock } from "./blocks/TeamProgressBlock";

// Grid-level stagger — each cell fades+slides in with a cascading delay.
// The individual blocks handle their own scale-in inside, so here we only
// do opacity + y-translate to avoid compounding transforms.
const GRID_VARIANTS: Variants = {
  animate: { transition: { staggerChildren: 0.07, delayChildren: 0.05 } },
};

const CELL_VARIANTS: Variants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.28, ease: [0.25, 0, 0, 1] } },
};

export function DashboardGrid() {
  return (
    <motion.div
      className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
      variants={GRID_VARIANTS}
      initial="initial"
      animate="animate"
    >
      <motion.div variants={CELL_VARIANTS}>
        <BlockErrorBoundary fallbackTitle="Greeting failed">
          <GreetingBlock />
        </BlockErrorBoundary>
      </motion.div>

      <motion.div variants={CELL_VARIANTS}>
        <BlockErrorBoundary fallbackTitle="Mission failed">
          <MissionBlock />
        </BlockErrorBoundary>
      </motion.div>

      <motion.div variants={CELL_VARIANTS}>
        <BlockErrorBoundary fallbackTitle="Trust level failed">
          <TrustLevelBlock />
        </BlockErrorBoundary>
      </motion.div>

      <motion.div variants={CELL_VARIANTS}>
        <BlockErrorBoundary fallbackTitle="Flashcards failed">
          <FlashcardsBlock />
        </BlockErrorBoundary>
      </motion.div>

      <motion.div variants={CELL_VARIANTS}>
        <BlockErrorBoundary fallbackTitle="Mastery failed">
          <MasteryBlock />
        </BlockErrorBoundary>
      </motion.div>

      <motion.div variants={CELL_VARIANTS}>
        <BlockErrorBoundary fallbackTitle="Activity failed">
          <ActivityBlock />
        </BlockErrorBoundary>
      </motion.div>

      <motion.div variants={CELL_VARIANTS} className="col-span-full">
        <BlockErrorBoundary fallbackTitle="Team progress failed">
          <TeamProgressBlock />
        </BlockErrorBoundary>
      </motion.div>
    </motion.div>
  );
}
