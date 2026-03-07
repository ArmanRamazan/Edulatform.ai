import type { Node, Edge } from "@xyflow/react";

// dagre does not ship TypeScript declarations — require + cast is the safe path.
// skipLibCheck is enabled in tsconfig.json so declaration files are not re-checked.
/* eslint-disable @typescript-eslint/no-require-imports */
const dagre = require("dagre") as DagreLib;

// ─── Minimal dagre type surface (only what we use) ────────────────────────────

interface DagreGraph {
  setDefaultEdgeLabel(fn: () => Record<string, unknown>): void;
  setGraph(opts: { rankdir: string; nodesep: number; ranksep: number }): void;
  setNode(id: string, opts: { width: number; height: number }): void;
  setEdge(source: string, target: string): void;
  node(id: string): { x: number; y: number } | undefined;
}

interface DagreLib {
  graphlib: { Graph: new () => DagreGraph };
  layout(g: DagreGraph): void;
}

// ─── Layout constants ─────────────────────────────────────────────────────────

/**
 * Node bounding-box used for dagre's rank/separation calculations.
 * Matches the maximum ConceptNode diameter (importance = 1 → 84 px).
 */
const NODE_WIDTH = 84;
const NODE_HEIGHT = 84;

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Applies a dagre top-to-bottom hierarchical layout to a set of React Flow nodes.
 *
 * Pure function — does not mutate inputs. Returns a new node array with updated
 * `position` values computed by dagre. Edges are only used for rank ordering;
 * their data is not modified.
 *
 * @param nodes  React Flow nodes — positions are overwritten by dagre.
 * @param edges  React Flow edges — source/target pairs define the DAG structure.
 * @returns      New node array with dagre-computed { x, y } positions.
 */
export function layoutGraph(nodes: Node[], edges: Edge[]): Node[] {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 80, ranksep: 120 });

  for (const node of nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }

  for (const edge of edges) {
    // Guard: dagre silently ignores edges whose endpoints were never registered,
    // but an explicit guard makes the contract clear.
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  return nodes.map((node) => {
    const n = g.node(node.id);
    if (!n) return node; // isolated node — keep original position
    return {
      ...node,
      position: {
        // dagre centers nodes; RF places them by top-left corner
        x: n.x - NODE_WIDTH / 2,
        y: n.y - NODE_HEIGHT / 2,
      },
    };
  });
}
