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
  type Edge,
  type NodeMouseHandler,
  type NodeTypes,
} from "@xyflow/react";
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
      {/* Subtle dot/line grid background */}
      <Background
        color="#1e1e2e"
        gap={24}
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
        maskColor="rgba(10, 10, 15, 0.75)"
        pannable
        zoomable
      />

      {/* Controls — bottom-left, violet accent on hover (via globals.css) */}
      <Controls position="bottom-left" showInteractive={false} />
    </ReactFlow>
  );
}
