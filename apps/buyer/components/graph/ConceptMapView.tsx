"use client";

import { useMemo, useState, useCallback, useEffect } from "react";
import { type Node, type Edge, MarkerType } from "@xyflow/react";
import { Upload, ChevronDown, AlertTriangle, RefreshCw, Network } from "lucide-react";
import { motion, LayoutGroup } from "framer-motion";
import { useAuth } from "@/hooks/use-auth";
import { useCourseGraph, useCourseMastery } from "@/hooks/use-concepts";
import { KnowledgeGraph } from "./KnowledgeGraph";
import { layoutGraph } from "@/lib/graph-layout";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ConceptData, MasteryItem } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

type FilterMode = "all" | "gaps" | "mastered";

export interface ConceptMapViewProps {
  /** Course ID whose concepts are visualised. */
  courseId: string;
  /**
   * Called with the clicked node's id — used by the parent to switch
   * to the Mind Map / Concept Hub for that node.
   */
  onNodeClick?: (nodeId: string) => void;
  /**
   * Optional upload handler. When provided, the empty state renders
   * an "Upload documents" CTA button.
   */
  onUpload?: () => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Converts a raw mastery fraction (0–1) to an integer percentage (0–100). */
function toMasteryPct(raw: number): number {
  return Math.round(raw * 100);
}

/** Returns mastery percentage for a concept id, or 0 if unknown. */
function getMastery(conceptId: string, items: MasteryItem[]): number {
  const item = items.find((m) => m.concept_id === conceptId);
  return item ? toMasteryPct(item.mastery) : 0;
}

/**
 * Computes a 0–1 importance score from in-degree:
 * concepts that more others depend on are rendered larger.
 */
function computeImportance(conceptId: string, allConcepts: ConceptData[]): number {
  const depCount = allConcepts.filter((c) => c.prerequisites.includes(conceptId)).length;
  const scale = Math.max(1, Math.ceil(allConcepts.length * 0.1));
  return Math.min(1, depCount / scale);
}

// ─── Graph data builder ───────────────────────────────────────────────────────

interface GraphData {
  baseNodes: Node[];
  baseEdges: Edge[];
}

function buildGraphData(concepts: ConceptData[], masteryItems: MasteryItem[]): GraphData {
  if (concepts.length === 0) return { baseNodes: [], baseEdges: [] };

  const rawNodes: Node[] = concepts.map((concept) => ({
    id: concept.id,
    type: "conceptNode",
    position: { x: 0, y: 0 }, // overwritten by layoutGraph
    data: {
      label: concept.name,
      mastery: getMastery(concept.id, masteryItems),
      importance: computeImportance(concept.id, concepts),
      category: concept.lesson_id ?? "",
    },
  }));

  const conceptIds = new Set(concepts.map((c) => c.id));
  const rawEdges: Edge[] = [];

  for (const concept of concepts) {
    for (const prereqId of concept.prerequisites) {
      if (!conceptIds.has(prereqId)) continue;

      rawEdges.push({
        id: `${prereqId}→${concept.id}`,
        source: prereqId,
        target: concept.id,
        animated: true,
        style: { stroke: "#7c5cfc", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#7c5cfc" },
      });
    }
  }

  const positioned = layoutGraph(rawNodes, rawEdges);
  return { baseNodes: positioned, baseEdges: rawEdges };
}

// ─── Overlay panel animation variants ────────────────────────────────────────

const overlayVariants = {
  hidden: { opacity: 0, y: -6, scale: 0.97 },
  visible: (delay: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.25,
      delay,
      ease: [0.16, 1, 0.3, 1] as [number, number, number, number],
    },
  }),
};

// ─── Filter mode cycle order ──────────────────────────────────────────────────

const FILTER_MODES: FilterMode[] = ["all", "gaps", "mastered"];

// ─── ConceptMapView ───────────────────────────────────────────────────────────

export function ConceptMapView({ courseId, onNodeClick, onUpload }: ConceptMapViewProps) {
  const { token } = useAuth();

  const {
    data: graph,
    isLoading: graphLoading,
    isError: graphError,
    refetch: refetchGraph,
  } = useCourseGraph(token, courseId);

  const {
    data: masteryData,
    isLoading: masteryLoading,
    isError: masteryError,
  } = useCourseMastery(token, courseId);

  const [filterMode, setFilterMode] = useState<FilterMode>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  const isLoading = graphLoading || masteryLoading;
  const masteryItems = masteryData?.items ?? [];

  // ── Keyboard shortcut: F cycles through All → Gaps → Mastered ──
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      )
        return;
      if (e.key === "f" || e.key === "F") {
        e.preventDefault();
        setFilterMode((prev) => {
          const idx = FILTER_MODES.indexOf(prev);
          return FILTER_MODES[(idx + 1) % FILTER_MODES.length];
        });
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, []);

  // ── Derived category list from lesson_id ──
  const categories = useMemo<string[]>(() => {
    if (!graph) return [];
    const seen = new Set<string>();
    for (const c of graph.concepts) {
      if (c.lesson_id) seen.add(c.lesson_id);
    }
    return Array.from(seen);
  }, [graph]);

  // ── Build dagre-positioned nodes + edges ──
  const { baseNodes, baseEdges } = useMemo<GraphData>(
    () => buildGraphData(graph?.concepts ?? [], masteryItems),
    // masteryItems changes identity on every render, so depend on masteryData
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [graph, masteryData],
  );

  // ── Apply filter: dim non-matching nodes rather than remove them ──
  const filteredNodes = useMemo<Node[]>(
    () =>
      baseNodes.map((node) => {
        const mastery = (node.data?.mastery as number) ?? 0;
        const category = (node.data?.category as string) ?? "";

        const matchesMode =
          filterMode === "all" ||
          (filterMode === "gaps" && mastery < 30) ||
          (filterMode === "mastered" && mastery >= 80);

        const matchesCategory =
          categoryFilter === "all" || category === categoryFilter;

        const visible = matchesMode && matchesCategory;

        return {
          ...node,
          style: {
            ...node.style,
            opacity: visible ? 1 : 0.1,
            transition: "opacity 0.35s cubic-bezier(0.16, 1, 0.3, 1)",
            pointerEvents: visible ? "auto" : ("none" as React.CSSProperties["pointerEvents"]),
          },
        };
      }),
    [baseNodes, filterMode, categoryFilter],
  );

  // ── Stats: always computed from full base nodes ──
  const stats = useMemo(() => {
    const total = baseNodes.length;
    const mastered = baseNodes.filter((n) => ((n.data?.mastery as number) ?? 0) >= 80).length;
    const gaps = baseNodes.filter((n) => ((n.data?.mastery as number) ?? 0) < 30).length;
    const masteryPct = total > 0 ? Math.round((mastered / total) * 100) : 0;
    return { total, mastered, gaps, masteryPct };
  }, [baseNodes]);

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      onNodeClick?.(nodeId);
    },
    [onNodeClick],
  );

  const handleRetry = useCallback(() => {
    void refetchGraph();
  }, [refetchGraph]);

  // ── Loading ──
  if (isLoading) {
    return <ConceptMapSkeleton />;
  }

  // ── Error — graph fetch failed (mastery error is non-fatal; 0% is used) ──
  if (graphError) {
    return <ConceptMapError onRetry={handleRetry} />;
  }

  // ── Empty ──
  if (!graph || graph.concepts.length === 0) {
    return <ConceptMapEmpty onUpload={onUpload} />;
  }

  const activeCategoryLabel =
    categoryFilter === "all"
      ? "Category"
      : categoryFilter.length > 14
        ? `${categoryFilter.slice(0, 13)}…`
        : categoryFilter;

  // ── Banner height offset: shift overlays down when mastery error banner shows ──
  const bannerOffset = masteryError ? 28 : 0;

  return (
    <div className="relative h-full min-h-[480px] w-full overflow-hidden rounded-xl">
      {/* ── Mastery error banner — non-fatal, mastery shows as 0% ────── */}
      {masteryError && (
        <motion.div
          className="absolute inset-x-0 top-0 z-20 flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs"
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          style={{
            background: "rgba(248, 113, 113, 0.08)",
            borderBottom: "1px solid rgba(248, 113, 113, 0.15)",
          }}
          role="alert"
        >
          <AlertTriangle className="size-3 shrink-0" style={{ color: "#f87171" }} aria-hidden="true" />
          <span style={{ color: "#f87171" }}>Mastery data unavailable — showing 0%</span>
        </motion.div>
      )}

      {/* ── Stats bar — top left ─────────────────────────────────────── */}
      <motion.div
        className="absolute left-3 z-10 flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium"
        custom={0}
        variants={overlayVariants}
        initial="hidden"
        animate="visible"
        style={{
          top: 12 + bannerOffset,
          transition: "top 0.2s ease",
          background: "rgba(10, 10, 15, 0.85)",
          border: "1px solid rgba(255, 255, 255, 0.07)",
          backdropFilter: "blur(10px)",
          WebkitBackdropFilter: "blur(10px)",
        }}
        role="status"
        aria-live="polite"
        aria-label="Graph statistics"
      >
        <span style={{ color: "#a0a0b0" }}>
          {stats.total} concept{stats.total !== 1 ? "s" : ""}
        </span>
        <span aria-hidden="true" style={{ color: "#2a2a45" }}>·</span>
        <span style={{ color: "#34d399" }}>{stats.mastered} mastered</span>
        <span aria-hidden="true" style={{ color: "#2a2a45" }}>·</span>
        <span style={{ color: "#f87171" }}>
          {stats.gaps} gap{stats.gaps !== 1 ? "s" : ""}
        </span>
        {/* Mastery percentage + mini progress bar */}
        <span
          aria-hidden="true"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            marginLeft: 2,
          }}
        >
          {/* Numeric % — monospaced so it doesn't jump width */}
          <span
            style={{
              color:
                stats.masteryPct >= 80
                  ? "#34d399"
                  : stats.masteryPct >= 40
                    ? "#7c5cfc"
                    : "#f87171",
              fontSize: 10,
              fontWeight: 600,
              fontFamily: "var(--font-mono, ui-monospace, monospace)",
              minWidth: "2.6ch",
              textAlign: "right",
            }}
          >
            {stats.masteryPct}%
          </span>
          {/* Bar */}
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              width: 36,
              height: 3,
              borderRadius: 2,
              background: "rgba(255,255,255,0.06)",
              overflow: "hidden",
            }}
          >
            <span
              style={{
                height: "100%",
                width: `${stats.masteryPct}%`,
                background:
                  stats.masteryPct >= 80
                    ? "#34d399"
                    : stats.masteryPct >= 40
                      ? "#7c5cfc"
                      : "#f87171",
                borderRadius: 2,
                transition: "width 0.8s cubic-bezier(0.16, 1, 0.3, 1)",
              }}
            />
          </span>
        </span>
      </motion.div>

      {/* ── Filter panel — top right ─────────────────────────────────── */}
      <motion.div
        className="absolute right-3 z-10 flex items-center gap-1 rounded-lg p-1"
        custom={0.06}
        variants={overlayVariants}
        initial="hidden"
        animate="visible"
        style={{
          top: 12 + bannerOffset,
          transition: "top 0.2s ease",
          background: "rgba(10, 10, 15, 0.85)",
          border: "1px solid rgba(255, 255, 255, 0.07)",
          backdropFilter: "blur(10px)",
          WebkitBackdropFilter: "blur(10px)",
        }}
        role="group"
        aria-label="Filter knowledge graph concepts (press F to cycle)"
      >
        {/* LayoutGroup scopes the layoutId sliding pill to this filter group only */}
        <LayoutGroup id="concept-map-filter">
          {(["all", "gaps", "mastered"] as const).map((mode) => {
            const isActive = filterMode === mode;
            // Short display label + accessible full description in title/aria-label
            const shortLabel =
              mode === "all" ? "All" : mode === "gaps" ? "Gaps" : "Mastered";
            const fullLabel =
              mode === "all"
                ? "Show all concepts"
                : mode === "gaps"
                  ? "Show gaps — mastery < 30%"
                  : "Show mastered — mastery ≥ 80%";
            return (
              <motion.button
                key={mode}
                type="button"
                onClick={() => setFilterMode(mode)}
                title={fullLabel}
                className={cn(
                  "relative rounded-[6px] px-2.5 py-1 text-xs font-medium",
                  "outline-none focus-visible:ring-2 focus-visible:ring-[#7c5cfc]",
                  "focus-visible:ring-offset-1 focus-visible:ring-offset-[#0a0a0f]",
                  isActive
                    ? "text-white"
                    : "text-[#6b6b80] hover:text-[#a0a0b0]",
                  "transition-colors duration-150 cursor-pointer",
                )}
                whileTap={{ scale: 0.92 }}
                aria-pressed={isActive}
                aria-label={fullLabel}
              >
                {/* Sliding active-pill indicator — animates between siblings via layoutId */}
                {isActive && (
                  <motion.span
                    layoutId="filter-active-pill"
                    className="absolute inset-0 rounded-[6px] bg-[#7c5cfc]"
                    style={{ zIndex: 0 }}
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                    aria-hidden="true"
                  />
                )}
                <span className="relative z-10">{shortLabel}</span>
              </motion.button>
            );
          })}
        </LayoutGroup>

        {/* Keyboard shortcut hint — "F" to cycle filters */}
        <div
          aria-hidden="true"
          className="mx-0.5 h-4 w-px"
          style={{ background: "rgba(255,255,255,0.07)" }}
        />
        <span
          className="rounded px-1.5 py-0.5 text-[9px] font-medium"
          style={{
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#6b6b80",
            fontFamily: "var(--font-mono, ui-monospace, monospace)",
          }}
          aria-hidden="true"
          title="Press F to cycle filters"
        >
          F
        </span>

        {/* Category dropdown — only rendered when at least one category exists */}
        {categories.length > 0 && (
          <>
            <div
              aria-hidden="true"
              className="mx-0.5 h-4 w-px"
              style={{ background: "rgba(255,255,255,0.07)" }}
            />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <motion.button
                  type="button"
                  className={cn(
                    "flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium",
                    "outline-none focus-visible:ring-2 focus-visible:ring-[#7c5cfc]",
                    "focus-visible:ring-offset-1 focus-visible:ring-offset-[#0a0a0f]",
                    "transition-colors duration-150",
                    categoryFilter !== "all"
                      ? "border border-[#7c5cfc]/25 bg-[#7c5cfc]/10 text-[#9b80fd] hover:bg-[#7c5cfc]/15"
                      : "border border-transparent bg-transparent text-[#6b6b80] hover:bg-white/5 hover:text-[#a0a0b0]",
                  )}
                  whileTap={{ scale: 0.92 }}
                  aria-label={
                    categoryFilter === "all"
                      ? "Filter by category"
                      : `Filtered by: ${categoryFilter}`
                  }
                >
                  {activeCategoryLabel}
                  <ChevronDown
                    className="size-3 transition-transform duration-150"
                    aria-hidden="true"
                    style={{ opacity: 0.7 }}
                  />
                </motion.button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="end"
                style={{
                  background: "#14141f",
                  border: "1px solid rgba(255,255,255,0.07)",
                  minWidth: 172,
                  boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
                }}
              >
                <DropdownMenuItem
                  onClick={() => setCategoryFilter("all")}
                  style={{
                    color: categoryFilter === "all" ? "#9b80fd" : "#a0a0b0",
                    fontSize: 12,
                  }}
                >
                  All categories
                </DropdownMenuItem>
                {categories.map((cat) => (
                  <DropdownMenuItem
                    key={cat}
                    onClick={() => setCategoryFilter(cat)}
                    style={{
                      color: categoryFilter === cat ? "#9b80fd" : "#a0a0b0",
                      fontSize: 12,
                    }}
                  >
                    {cat}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        )}
      </motion.div>

      {/* ── Knowledge graph canvas ── */}
      <KnowledgeGraph
        nodes={filteredNodes}
        edges={baseEdges}
        onNodeClick={handleNodeClick}
        viewMode="map"
      />
    </div>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function ConceptMapSkeleton() {
  return (
    <div
      className="relative h-full min-h-[480px] w-full overflow-hidden rounded-xl"
      style={{ background: "#0a0a0f" }}
      role="status"
      aria-busy="true"
      aria-label="Loading concept map…"
    >
      {/* Dot-grid texture — matches the live canvas background */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: "radial-gradient(circle, #22223a 1px, transparent 1px)",
          backgroundSize: "28px 28px",
          opacity: 0.4,
        }}
        aria-hidden="true"
      />

      {/* Abstract tree skeleton (1 root → 3 mid → 5 leaf) */}
      <svg
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 720 440"
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        {/* Edges */}
        {(
          [
            [360, 80, 200, 200],
            [360, 80, 360, 200],
            [360, 80, 520, 200],
            [200, 200, 130, 340],
            [200, 200, 260, 340],
            [360, 200, 360, 340],
            [520, 200, 460, 340],
            [520, 200, 590, 340],
          ] as [number, number, number, number][]
        ).map(([x1, y1, x2, y2], i) => (
          <line
            key={i}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke="#22223a"
            strokeWidth="1.5"
            strokeDasharray="6 4"
          />
        ))}

        {/* Root node — violet ring hint */}
        <circle cx="360" cy="80" r="32" fill="#14141f" stroke="#2a2a3e" strokeWidth="1.5" />
        <circle
          cx="360"
          cy="80"
          r="32"
          fill="none"
          stroke="#7c5cfc"
          strokeWidth="1.5"
          strokeOpacity="0.25"
        />
        <rect x="342" y="74" width="36" height="6" rx="3" fill="#22223a" />

        {/* Mid-tier nodes */}
        {(
          [
            [200, 200, 26],
            [360, 200, 26],
            [520, 200, 26],
          ] as [number, number, number][]
        ).map(([cx, cy, r], i) => (
          <g key={i}>
            <circle cx={cx} cy={cy} r={r} fill="#14141f" stroke="#1e1e2e" strokeWidth="1.5" />
            <rect x={cx - 12} y={cy - 3} width="24" height="5" rx="2.5" fill="#1e1e2e" />
          </g>
        ))}

        {/* Leaf nodes — staggered opacity pulse for depth */}
        {(
          [
            [130, 340, 20],
            [260, 340, 20],
            [360, 340, 20],
            [460, 340, 20],
            [590, 340, 20],
          ] as [number, number, number][]
        ).map(([cx, cy, r], i) => (
          <g key={i} style={{ opacity: 0.6 + i * 0.08 }}>
            <circle cx={cx} cy={cy} r={r} fill="#14141f" stroke="#1e1e2e" strokeWidth="1" />
            <rect x={cx - 10} y={cy - 2.5} width="20" height="4" rx="2" fill="#1e1e2e" />
          </g>
        ))}
      </svg>

      {/* Full-canvas shimmer sweep */}
      <div
        className="animate-shimmer pointer-events-none absolute inset-0"
        aria-hidden="true"
      />

      {/* Placeholder chrome for the stats + filter overlays */}
      <div
        className="absolute left-3 top-3 h-7 w-56 rounded-lg"
        style={{ background: "#14141f", border: "1px solid rgba(255,255,255,0.05)" }}
        aria-hidden="true"
      />
      <div
        className="absolute right-3 top-3 h-7 w-64 rounded-lg"
        style={{ background: "#14141f", border: "1px solid rgba(255,255,255,0.05)" }}
        aria-hidden="true"
      />
    </div>
  );
}

// ─── Error state ──────────────────────────────────────────────────────────────

function ConceptMapError({ onRetry }: { onRetry?: () => void }) {
  return (
    <motion.div
      className="flex h-full min-h-[480px] w-full flex-col items-center justify-center gap-5 rounded-xl"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      style={{
        background: "#0a0a0f",
        backgroundImage: "radial-gradient(circle, #22223a 1px, transparent 1px)",
        backgroundSize: "28px 28px",
      }}
      role="alert"
      aria-label="Failed to load knowledge graph"
    >
      {/* Concentric ring decoration — red tint */}
      <div className="relative flex items-center justify-center">
        <div
          className="absolute size-48 rounded-full"
          style={{ border: "1px dashed rgba(248, 113, 113, 0.12)", opacity: 0.6 }}
          aria-hidden="true"
        />
        <div
          className="absolute size-32 rounded-full"
          style={{ border: "1px solid rgba(248, 113, 113, 0.08)" }}
          aria-hidden="true"
        />
        <motion.div
          className="flex size-16 items-center justify-center rounded-full"
          style={{
            background: "rgba(248, 113, 113, 0.06)",
            border: "1px solid rgba(248, 113, 113, 0.2)",
          }}
          animate={{
            boxShadow: [
              "0 0 0px rgba(248, 113, 113, 0)",
              "0 0 20px rgba(248, 113, 113, 0.12)",
              "0 0 0px rgba(248, 113, 113, 0)",
            ],
          }}
          transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
        >
          <AlertTriangle
            className="size-7"
            style={{ color: "#f87171" }}
            strokeWidth={1.5}
            aria-hidden="true"
          />
        </motion.div>
      </div>

      <div className="text-center">
        <p className="text-sm font-semibold" style={{ color: "#e2e2e8" }}>
          Failed to load knowledge graph
        </p>
        <p className="mt-1 text-xs" style={{ color: "#6b6b80" }}>
          Check your connection and try again
        </p>
      </div>

      {onRetry && (
        <motion.button
          type="button"
          onClick={onRetry}
          className={cn(
            "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium",
            "outline-none focus-visible:ring-2 focus-visible:ring-[#7c5cfc]",
            "transition-colors duration-150",
            "border border-white/[0.07] bg-[#14141f] text-[#a0a0b0]",
            "hover:border-white/[0.12] hover:text-[#e2e2e8]",
          )}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.96 }}
          aria-label="Retry loading knowledge graph"
        >
          <RefreshCw className="size-3" aria-hidden="true" />
          Retry
        </motion.button>
      )}
    </motion.div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function ConceptMapEmpty({ onUpload }: { onUpload?: () => void }) {
  return (
    <motion.div
      className="flex h-full min-h-[480px] w-full flex-col items-center justify-center gap-5 rounded-xl"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.25 }}
      style={{
        background: "#0a0a0f",
        backgroundImage: "radial-gradient(circle, #22223a 1px, transparent 1px)",
        backgroundSize: "28px 28px",
      }}
      role="region"
      aria-label="Knowledge graph — empty"
    >
      {/* Concentric ring decoration */}
      <div className="relative flex items-center justify-center">
        <motion.div
          className="absolute size-48 rounded-full"
          style={{ border: "1px dashed rgba(255,255,255,0.05)" }}
          animate={{ rotate: 360 }}
          transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
          aria-hidden="true"
        />
        <div
          className="absolute size-32 rounded-full"
          style={{ border: "1px solid rgba(255,255,255,0.04)" }}
          aria-hidden="true"
        />
        <div
          className="flex size-16 items-center justify-center rounded-full"
          style={{
            background: "#14141f",
            border: "1px solid rgba(255,255,255,0.07)",
          }}
        >
          <Network
            className="size-7"
            style={{ color: "#6b6b80" }}
            strokeWidth={1.5}
            aria-hidden="true"
          />
        </div>
      </div>

      <div className="text-center">
        <p className="text-sm font-semibold" style={{ color: "#a0a0b0" }}>
          No concepts yet
        </p>
        <p className="mt-1 max-w-[260px] text-xs leading-relaxed" style={{ color: "#6b6b80" }}>
          {onUpload
            ? "Upload documents to build your knowledge graph — concepts and relationships appear automatically"
            : "Concepts will appear here once documents are added to the knowledge base"}
        </p>
      </div>

      {onUpload && (
        <motion.button
          type="button"
          onClick={onUpload}
          className={cn(
            "flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold",
            "outline-none focus-visible:ring-2 focus-visible:ring-[#7c5cfc]",
            "focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a0f]",
            "bg-[#7c5cfc] text-white transition-colors duration-150 hover:bg-[#6b4fe0]",
          )}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
        >
          <Upload className="size-3.5" aria-hidden="true" />
          Upload documents
        </motion.button>
      )}
    </motion.div>
  );
}
