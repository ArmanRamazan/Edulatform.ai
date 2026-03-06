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
      <Skeleton className="h-full w-full rounded-xl" />
    ),
  },
);
