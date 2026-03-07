"use client";

import { useMemo, useState, useCallback } from "react";
import { type Node, type Edge, MarkerType } from "@xyflow/react";
import { Upload, ChevronDown } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useCourseGraph, useCourseMastery } from "@/hooks/use-concepts";
import { KnowledgeGraph } from "./KnowledgeGraph";
import { layoutGraph } from "@/lib/graph-layout";
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
 * Scale is relative to 10 % of the graph so single outliers don't
 * saturate the maximum size.
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
      // Skip dangling references (prerequisite concept not in this graph)
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

// ─── ConceptMapView ───────────────────────────────────────────────────────────

export function ConceptMapView({ courseId, onNodeClick }: ConceptMapViewProps) {
  const { token } = useAuth();

  const { data: graph, isLoading: graphLoading } = useCourseGraph(token, courseId);
  const { data: masteryData, isLoading: masteryLoading } = useCourseMastery(token, courseId);

  const [filterMode, setFilterMode] = useState<FilterMode>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  const isLoading = graphLoading || masteryLoading;
  const masteryItems = masteryData?.items ?? [];

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
  // This keeps dagre positions stable so the layout doesn't jump.
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
            // CSS transition for smooth fade — works because React Flow applies
            // style directly to the node's DOM wrapper element.
            opacity: visible ? 1 : 0.12,
            transition: "opacity 0.3s ease",
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
    return { total, mastered, gaps };
  }, [baseNodes]);

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      onNodeClick?.(nodeId);
    },
    [onNodeClick],
  );

  // ── Loading ──
  if (isLoading) {
    return <ConceptMapSkeleton />;
  }

  // ── Empty ──
  if (!graph || graph.concepts.length === 0) {
    return <ConceptMapEmpty />;
  }

  return (
    <div className="relative h-full min-h-[480px] w-full overflow-hidden rounded-xl">
      {/* ── Stats bar — top left ─────────────────────────────────────── */}
      <div
        className="absolute left-3 top-3 z-10 flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium"
        style={{
          background: "rgba(10, 10, 15, 0.82)",
          border: "1px solid #1e1e2e",
          backdropFilter: "blur(8px)",
          WebkitBackdropFilter: "blur(8px)",
        }}
        role="status"
        aria-live="polite"
        aria-label="Graph statistics"
      >
        <span style={{ color: "#a0a0b0" }}>
          {stats.total} concept{stats.total !== 1 ? "s" : ""}
        </span>
        <span aria-hidden="true" style={{ color: "#2a2a45" }}>·</span>
        <span style={{ color: "#34d399" }}>
          {stats.mastered} mastered
        </span>
        <span aria-hidden="true" style={{ color: "#2a2a45" }}>·</span>
        <span style={{ color: "#f87171" }}>
          {stats.gaps} gap{stats.gaps !== 1 ? "s" : ""}
        </span>
      </div>

      {/* ── Filter panel — top right ─────────────────────────────────── */}
      <div
        className="absolute right-3 top-3 z-10 flex items-center gap-1 rounded-lg p-1"
        style={{
          background: "rgba(10, 10, 15, 0.82)",
          border: "1px solid #1e1e2e",
          backdropFilter: "blur(8px)",
          WebkitBackdropFilter: "blur(8px)",
        }}
        role="group"
        aria-label="Filter knowledge graph concepts"
      >
        {(["all", "gaps", "mastered"] as const).map((mode) => (
          <button
            key={mode}
            type="button"
            onClick={() => setFilterMode(mode)}
            className="rounded px-2.5 py-1 text-xs font-medium"
            style={{
              background: filterMode === mode ? "#7c5cfc" : "transparent",
              color: filterMode === mode ? "#ffffff" : "#6b6b80",
              transition: "background 0.2s ease, color 0.2s ease",
            }}
            aria-pressed={filterMode === mode}
          >
            {mode === "all" ? "All" : mode === "gaps" ? "Gaps <30%" : "Mastered >80%"}
          </button>
        ))}

        {/* Category dropdown — only rendered when at least one category exists */}
        {categories.length > 0 && (
          <>
            <div
              aria-hidden="true"
              className="mx-0.5 h-4 w-px"
              style={{ background: "#1e1e2e" }}
            />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium"
                  style={{
                    background: categoryFilter !== "all" ? "#18182a" : "transparent",
                    color: categoryFilter !== "all" ? "#7c5cfc" : "#6b6b80",
                    border:
                      categoryFilter !== "all"
                        ? "1px solid #2a2a4a"
                        : "1px solid transparent",
                    transition: "all 0.2s ease",
                  }}
                  aria-label={
                    categoryFilter === "all"
                      ? "Filter by category"
                      : `Filtered by category: ${categoryFilter}`
                  }
                >
                  Category
                  <ChevronDown className="size-3" aria-hidden="true" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="end"
                style={{
                  background: "#14141f",
                  border: "1px solid #1e1e2e",
                  minWidth: 168,
                }}
              >
                <DropdownMenuItem
                  onClick={() => setCategoryFilter("all")}
                  style={{
                    color: categoryFilter === "all" ? "#7c5cfc" : "#a0a0b0",
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
                      color: categoryFilter === cat ? "#7c5cfc" : "#a0a0b0",
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
      </div>

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

        {/* Root node */}
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

        {/* Leaf nodes */}
        {(
          [
            [130, 340, 20],
            [260, 340, 20],
            [360, 340, 20],
            [460, 340, 20],
            [590, 340, 20],
          ] as [number, number, number][]
        ).map(([cx, cy, r], i) => (
          <g key={i}>
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
        style={{ background: "#14141f", border: "1px solid #1e1e2e" }}
        aria-hidden="true"
      />
      <div
        className="absolute right-3 top-3 h-7 w-64 rounded-lg"
        style={{ background: "#14141f", border: "1px solid #1e1e2e" }}
        aria-hidden="true"
      />
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function ConceptMapEmpty() {
  return (
    <div
      className="flex h-full min-h-[480px] w-full flex-col items-center justify-center gap-5 rounded-xl"
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
        <div
          className="absolute size-48 rounded-full"
          style={{ border: "1px dashed #1e1e2e", opacity: 0.5 }}
          aria-hidden="true"
        />
        <div
          className="absolute size-32 rounded-full"
          style={{ border: "1px solid #1e1e2e" }}
          aria-hidden="true"
        />
        <div
          className="flex size-16 items-center justify-center rounded-full"
          style={{ background: "#14141f", border: "1px solid #2a2a3e" }}
        >
          <Upload
            className="size-7"
            style={{ color: "#6b6b80" }}
            strokeWidth={1.5}
            aria-hidden="true"
          />
        </div>
      </div>

      <div className="text-center">
        <p className="text-sm font-semibold" style={{ color: "#a0a0b0" }}>
          Upload documents to build your knowledge graph
        </p>
        <p className="mt-1 text-xs" style={{ color: "#6b6b80" }}>
          Concepts and their relationships will appear here automatically
        </p>
      </div>
    </div>
  );
}
