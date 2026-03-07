"use client";

import { useState, useCallback, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { MousePointer2 } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useCourseGraph, useCourseMastery } from "@/hooks/use-concepts";
import { ConceptMapView } from "./ConceptMapView";
import { MindMapView } from "./MindMapView";

// ─── Types ────────────────────────────────────────────────────────────────────

type ViewMode = "map" | "mindmap";
type NavDirection = "forward" | "back";

export interface GraphViewProps {
  /** Course ID whose knowledge graph is visualised. */
  courseId: string;
}

// ─── Animation variants ───────────────────────────────────────────────────────
//
// Directional transitions communicate spatial hierarchy:
//   forward (map → mindmap): feel like "zooming into" a selected node
//     – exiting map scales up slightly; entering mindmap scales down from larger
//   back    (mindmap → map): feel like "zooming out" to the overview
//     – exiting mindmap scales down; entering map scales up from smaller

const viewVariants = {
  initial: (dir: NavDirection) => ({
    opacity: 0,
    scale: dir === "forward" ? 1.04 : 0.96,
  }),
  animate: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.28, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
  },
  exit: (dir: NavDirection) => ({
    opacity: 0,
    scale: dir === "forward" ? 0.96 : 1.04,
    transition: { duration: 0.2, ease: [0.4, 0, 1, 1] as [number, number, number, number] },
  }),
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
  // Track nav direction so variants can animate spatially (forward = zoom in, back = zoom out).
  const [direction, setDirection] = useState<NavDirection>("forward");
  // First-run hint: show "Click a concept to explore" for 5 s, dismiss on first interaction.
  const [showHint, setShowHint] = useState(true);

  // Auto-dismiss hint after 5 s from mount.
  useEffect(() => {
    if (!showHint) return;
    const t = setTimeout(() => setShowHint(false), 5000);
    return () => clearTimeout(t);
  }, [showHint]);

  // Pre-fetch graph data so MindMapView receives it without an extra request.
  // ConceptMapView also calls useCourseGraph internally; TanStack Query
  // deduplicates and serves from cache.
  const { data: graph } = useCourseGraph(token, courseId);
  const { data: masteryData } = useCourseMastery(token, courseId);

  const handleNodeClick = useCallback((nodeId: string) => {
    setShowHint(false);
    setDirection("forward");
    setSelectedConceptId(nodeId);
    setViewMode("mindmap");
  }, []);

  const handleBack = useCallback(() => {
    setDirection("back");
    setViewMode("map");
    setSelectedConceptId(null);
  }, []);

  // Derive the active key for AnimatePresence so the MindMap key changes when
  // the user navigates from one concept to another without returning to map view.
  // When mindmap is requested but graph data is still loading, keep key="map"
  // so ConceptMapView stays mounted without a spurious transition — it will
  // seamlessly hand off to the mindmap key once graph is available.
  const animKey =
    viewMode === "map"
      ? "map"
      : selectedConceptId && graph
        ? `mindmap-${selectedConceptId}`
        : "map"; // graph not yet ready — stay on map key, no transition

  return (
    // Outer container fades in on mount so the page never pops in abruptly.
    <motion.div
      className="relative h-full w-full overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      <AnimatePresence mode="wait" custom={direction} initial={false}>
        {viewMode === "map" || !selectedConceptId || !graph ? (
          // Map view — also used as a waiting state while graph data loads.
          <motion.div
            key={animKey}
            className="absolute inset-0"
            custom={direction}
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
        ) : (
          // Mind-map view — only rendered when graph data is confirmed present.
          <motion.div
            key={animKey}
            className="absolute inset-0"
            custom={direction}
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
        )}
      </AnimatePresence>

      {/* ── First-run hint: "Click a concept to explore its connections" ── */}
      {/* Appears 1.5 s after mount, auto-dismisses at 5 s or on first node click.  */}
      {/* pointer-events-none so it never blocks map interaction.                    */}
      <AnimatePresence>
        {viewMode === "map" && showHint && (
          <motion.div
            key="map-hint"
            className="pointer-events-none absolute bottom-16 left-1/2 z-20 flex -translate-x-1/2 items-center gap-2 rounded-full px-3.5 py-2 text-xs"
            style={{
              background: "rgba(10, 10, 15, 0.82)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              backdropFilter: "blur(12px)",
              WebkitBackdropFilter: "blur(12px)",
              color: "#6b6b80",
              whiteSpace: "nowrap",
            }}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0, transition: { delay: 1.4, duration: 0.3 } }}
            exit={{ opacity: 0, y: 3, transition: { duration: 0.2 } }}
            aria-hidden="true"
          >
            <MousePointer2
              className="size-3 shrink-0"
              style={{ color: "#7c5cfc" }}
              aria-hidden="true"
            />
            Click any concept to explore its connections
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
