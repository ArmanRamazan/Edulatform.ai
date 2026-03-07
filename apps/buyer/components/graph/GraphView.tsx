"use client";

import { useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useAuth } from "@/hooks/use-auth";
import { useCourseGraph, useCourseMastery } from "@/hooks/use-concepts";
import { ConceptMapView } from "./ConceptMapView";
import { MindMapView } from "./MindMapView";

// ─── Types ────────────────────────────────────────────────────────────────────

type ViewMode = "map" | "mindmap";

export interface GraphViewProps {
  /** Course ID whose knowledge graph is visualised. */
  courseId: string;
}

// ─── Animation variants ───────────────────────────────────────────────────────

const viewVariants = {
  initial: { opacity: 0, scale: 0.985 },
  animate: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.28, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
  },
  exit: {
    opacity: 0,
    scale: 0.985,
    transition: { duration: 0.18, ease: [0.4, 0, 1, 1] as [number, number, number, number] },
  },
};

// ─── GraphView ────────────────────────────────────────────────────────────────

/**
 * Top-level graph orchestrator.
 *
 * Fetches course graph data once and manages the two-view toggle:
 *   map     → ConceptMapView  (full course overview, zoomable canvas)
 *   mindmap → MindMapView     (radial focus view for a single concept)
 *
 * Clicking a node in map-mode transitions to mindmap-mode for that concept.
 * The "Back" button in mindmap-mode transitions back to the map.
 *
 * Both child views share the same TanStack Query cache entry — no duplicate
 * network requests are made.
 */
export function GraphView({ courseId }: GraphViewProps) {
  const { token } = useAuth();

  const [viewMode, setViewMode] = useState<ViewMode>("map");
  const [selectedConceptId, setSelectedConceptId] = useState<string | null>(null);

  // Pre-fetch graph data so MindMapView receives it without an extra request.
  // ConceptMapView also calls useCourseGraph internally; TanStack Query
  // deduplicates and serves from cache.
  const { data: graph } = useCourseGraph(token, courseId);
  const { data: masteryData } = useCourseMastery(token, courseId);

  const handleNodeClick = useCallback((nodeId: string) => {
    setSelectedConceptId(nodeId);
    setViewMode("mindmap");
  }, []);

  const handleBack = useCallback(() => {
    setViewMode("map");
    setSelectedConceptId(null);
  }, []);

  // Derive the active key for AnimatePresence so the MindMap key changes when
  // the user navigates from one concept to another without returning to map view.
  const animKey =
    viewMode === "map" ? "map" : `mindmap-${selectedConceptId ?? "none"}`;

  return (
    <div className="relative h-full w-full overflow-hidden">
      <AnimatePresence mode="wait" initial={false}>
        {viewMode === "map" ? (
          <motion.div
            key={animKey}
            className="absolute inset-0"
            variants={viewVariants}
            initial="initial"
            animate="animate"
            exit="exit"
          >
            <ConceptMapView
              courseId={courseId}
              onNodeClick={handleNodeClick}
            />
          </motion.div>
        ) : selectedConceptId && graph ? (
          <motion.div
            key={animKey}
            className="absolute inset-0"
            variants={viewVariants}
            initial="initial"
            animate="animate"
            exit="exit"
          >
            <MindMapView
              conceptId={selectedConceptId}
              graphData={graph}
              masteryItems={masteryData?.items ?? []}
              onBack={handleBack}
              onNodeClick={handleNodeClick}
            />
          </motion.div>
        ) : (
          // Fallback: graph data not ready yet — show map view which handles
          // its own loading skeleton.
          <motion.div
            key="map-fallback"
            className="absolute inset-0"
            variants={viewVariants}
            initial="initial"
            animate="animate"
            exit="exit"
          >
            <ConceptMapView
              courseId={courseId}
              onNodeClick={handleNodeClick}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
