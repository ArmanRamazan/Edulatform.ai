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
      <div className="relative h-full min-h-[480px] w-full overflow-hidden rounded-xl">
        <Skeleton className="absolute inset-0 h-full w-full" />
        {/* Ghost nodes hint at the graph structure below */}
        <div className="absolute inset-0 flex items-center justify-center gap-16 opacity-25">
          <Skeleton className="size-16 rounded-full" />
          <div className="flex flex-col gap-10">
            <Skeleton className="size-12 rounded-full" />
            <Skeleton className="size-12 rounded-full" />
          </div>
          <Skeleton className="size-14 rounded-full" />
        </div>
      </div>
    ),
  },
);
