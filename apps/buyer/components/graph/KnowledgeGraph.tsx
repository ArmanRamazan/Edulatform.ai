"use client";

import dynamic from "next/dynamic";
import type { Node, Edge } from "@xyflow/react";
import { Skeleton } from "@/components/ui/skeleton";

// ─── Public props contract ────────────────────────────────────────────────────

export interface KnowledgeGraphProps {
  /** React Flow node array — include `type: "conceptNode"` to use ConceptNode */
  nodes: Node[];
  /** React Flow edge array */
  edges: Edge[];
  /** Called with the clicked node's id */
  onNodeClick: (nodeId: string) => void;
  /** 'map' = dot-grid background | 'mindmap' = line-grid background */
  viewMode: "map" | "mindmap";
}

// ─── SSR-safe dynamic wrapper ─────────────────────────────────────────────────
//
// React Flow uses browser-only APIs (ResizeObserver, window, etc.) at module
// load time, so we must disable SSR for the implementation module.

export const KnowledgeGraph = dynamic<KnowledgeGraphProps>(
  () =>
    import("./KnowledgeGraphImpl").then((mod) => ({
      default: mod.KnowledgeGraphImpl,
    })),
  {
    ssr: false,
    loading: () => (
      <div
        className="relative h-full min-h-[480px] w-full overflow-hidden rounded-xl"
        style={{ background: "#0a0a0f" }}
        aria-busy="true"
        aria-label="Loading knowledge graph…"
      >
        {/* Dot-grid background — matches the real canvas */}
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: "radial-gradient(circle, #22223a 1px, transparent 1px)",
            backgroundSize: "28px 28px",
            opacity: 0.4,
          }}
        />

        {/* SVG skeleton graph — 1 hub + 4 satellite nodes with connecting lines */}
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 600 360"
          preserveAspectRatio="xMidYMid meet"
          aria-hidden="true"
        >
          {/* Connection lines */}
          {[
            [300, 180, 160, 100],
            [300, 180, 440, 100],
            [300, 180, 150, 270],
            [300, 180, 450, 270],
          ].map(([x1, y1, x2, y2], i) => (
            <line
              key={i}
              x1={x1} y1={y1} x2={x2} y2={y2}
              stroke="#22223a"
              strokeWidth="1.5"
              strokeDasharray="6 4"
            />
          ))}

          {/* Hub node */}
          <circle cx="300" cy="180" r="38" fill="#14141f" stroke="#2a2a3e" strokeWidth="1.5" />
          <circle cx="300" cy="180" r="38" fill="none" stroke="#7c5cfc" strokeWidth="1.5" strokeOpacity="0.25" />

          {/* Satellite nodes */}
          {[
            [160, 100, 28],
            [440, 100, 24],
            [150, 270, 26],
            [450, 270, 22],
          ].map(([cx, cy, r], i) => (
            <circle key={i} cx={cx} cy={cy} r={r} fill="#14141f" stroke="#1e1e2e" strokeWidth="1.5" />
          ))}

          {/* Skeleton shimmer lines inside nodes */}
          <rect x="280" y="174" width="40" height="6" rx="3" fill="#22223a" />
          {[
            [147, 95, 24],
            [428, 95, 20],
            [137, 265, 22],
            [439, 265, 18],
          ].map(([x, y, w], i) => (
            <rect key={i} x={x} y={y} width={w} height="5" rx="2.5" fill="#1e1e2e" />
          ))}
        </svg>

        {/* Full-canvas shimmer sweep — left-to-right highlight passes over the skeleton graph */}
        <div
          className="animate-shimmer pointer-events-none absolute inset-0"
          aria-hidden="true"
        />

        {/* Skeleton placeholders for Controls and MiniMap positions */}
        <Skeleton className="absolute bottom-4 left-4 h-24 w-8 rounded-lg opacity-50" />
        <Skeleton className="absolute bottom-4 right-4 h-20 w-20 rounded-lg opacity-40" />
      </div>
    ),
  },
);
