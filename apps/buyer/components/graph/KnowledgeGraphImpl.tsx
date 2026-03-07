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
import { Network } from "lucide-react";
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

  // Empty state — render an atmospheric placeholder rather than a blank rect
  if (nodes.length === 0) {
    return (
      <div
        className="flex h-full min-h-[480px] w-full flex-col items-center justify-center gap-4 rounded-xl"
        style={{
          background: "#0a0a0f",
          // Subtle dot grid — same visual language as the real canvas
          backgroundImage:
            "radial-gradient(circle, #22223a 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
        role="region"
        aria-label="Knowledge graph — empty"
      >
        {/* Faint concentric rings give spatial depth */}
        <div className="relative flex items-center justify-center">
          <div
            className="absolute size-40 rounded-full"
            style={{ border: "1px solid #22223a" }}
          />
          <div
            className="absolute size-24 rounded-full"
            style={{ border: "1px solid #1e1e2e" }}
          />
          <div
            className="flex size-14 items-center justify-center rounded-full"
            style={{ background: "#14141f", border: "1px solid #2a2a3e" }}
          >
            <Network className="size-6 text-[#6b6b80]" strokeWidth={1.5} />
          </div>
        </div>
        <div className="text-center">
          <p className="text-sm font-semibold text-[#a0a0b0]">No concepts yet</p>
          <p className="mt-1 text-xs text-[#6b6b80]">
            Add concepts to the knowledge base to map them here
          </p>
        </div>
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
      {/* Grid texture — mindmap uses a slightly more visible line grid for hierarchy,
          map uses a near-invisible dot grid so nodes feel free-floating */}
      <Background
        color={viewMode === "mindmap" ? "#1e1e2e" : "#22223a"}
        gap={viewMode === "mindmap" ? 32 : 28}
        size={viewMode === "mindmap" ? 0.5 : 1}
        variant={backgroundVariant}
        style={{ opacity: viewMode === "mindmap" ? 0.6 : 0.4 }}
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
