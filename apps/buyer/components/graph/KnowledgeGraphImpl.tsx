"use client";

import "@xyflow/react/dist/style.css";

import { useCallback } from "react";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  type Node,
  type NodeMouseHandler,
  type NodeTypes,
} from "@xyflow/react";
import { GitMerge } from "lucide-react";
import { ConceptNode } from "./ConceptNode";
import { defaultEdgeOptions, minimapNodeColor } from "./graphTheme";
import type { KnowledgeGraphProps } from "./KnowledgeGraph";

// Register custom node types outside of render to avoid re-creation on each render
const nodeTypes: NodeTypes = {
  conceptNode: ConceptNode,
};

export function KnowledgeGraphImpl({
  nodes,
  edges,
  onNodeClick,
  viewMode,
}: KnowledgeGraphProps) {
  const handleNodeClick = useCallback<NodeMouseHandler>(
    (_, node) => {
      onNodeClick(node.id);
    },
    [onNodeClick],
  );

  // 'mindmap' uses lines for a cleaner hierarchical feel; 'map' uses dots
  const backgroundVariant =
    viewMode === "mindmap" ? BackgroundVariant.Lines : BackgroundVariant.Dots;

  // Empty state — render a placeholder canvas rather than a blank rect
  if (nodes.length === 0) {
    return (
      <div
        className="flex h-full min-h-[480px] w-full flex-col items-center justify-center gap-3 rounded-xl"
        style={{ background: "#0a0a0f" }}
      >
        <GitMerge className="size-10 text-[#22223a]" strokeWidth={1.5} />
        <p className="text-sm font-medium text-[#6b6b80]">No concepts in graph</p>
        <p className="text-xs text-[#4a4a5a]">Add concepts to the knowledge base to see them here</p>
      </div>
    );
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodeClick={handleNodeClick}
      defaultEdgeOptions={defaultEdgeOptions}
      proOptions={{ hideAttribution: true }}
      fitView
      fitViewOptions={{ padding: 0.15 }}
      colorMode="dark"
      deleteKeyCode={null}
      style={{ background: "#0a0a0f" }}
    >
      {/* Subtle dot/line grid — very low opacity to avoid competing with nodes.
          'mindmap': dim line grid | 'map': near-invisible white dots */}
      <Background
        color={viewMode === "mindmap" ? "#2a2a3e" : "#2a2a3e"}
        gap={28}
        size={1}
        variant={backgroundVariant}
      />

      {/* Minimap — bottom-right, dark styled */}
      <MiniMap
        position="bottom-right"
        style={{
          background: "#0e0e18",
          border: "1px solid #1e1e2e",
          borderRadius: 8,
        }}
        nodeColor={(node: Node) =>
          minimapNodeColor((node.data?.mastery as number) ?? 0)
        }
        maskColor="rgba(10, 10, 15, 0.82)"
        pannable
        zoomable
      />

      {/* Controls — bottom-left, violet accent on hover (via globals.css) */}
      <Controls position="bottom-left" showInteractive={false} />
    </ReactFlow>
  );
}
