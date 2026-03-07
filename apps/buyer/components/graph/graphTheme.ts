import type { CSSProperties } from "react";
import { MarkerType } from "@xyflow/react";

// ─── Mastery color scale ──────────────────────────────────────────────────────
export const MASTERY_COLORS = {
  zero: "#6b6b80",
  mid: "#7c5cfc",
  full: "#34d399",
} as const;

/**
 * Returns an accent color based on mastery percentage.
 * 0% → muted gray | ~50% → violet primary | 100% → emerald success
 */
export function masteryColor(pct: number): string {
  if (pct >= 80) return MASTERY_COLORS.full;
  if (pct >= 30) return MASTERY_COLORS.mid;
  return MASTERY_COLORS.zero;
}

// ─── Node styles ─────────────────────────────────────────────────────────────
export const defaultNodeStyle: CSSProperties = {
  background: "#14141f",
  border: "1px solid #1e1e2e",
  borderRadius: "50%",
  color: "#e2e2e8",
  padding: 0,
};

// ─── Edge styles ─────────────────────────────────────────────────────────────

/** Prerequisite relationship: solid violet line with arrowhead */
export const prerequisiteEdgeStyle: CSSProperties = {
  stroke: "#7c5cfc",
  strokeWidth: 2,
};

/** Related concept connection: dashed muted line, no arrowhead */
export const relatedEdgeStyle: CSSProperties = {
  stroke: "#6b6b80",
  strokeWidth: 1.5,
  strokeDasharray: "6 4",
};

/**
 * Defaults applied to all prerequisite edges.
 * Animated flow line with a closed violet arrowhead.
 */
export const defaultEdgeOptions = {
  animated: true,
  style: prerequisiteEdgeStyle,
  markerEnd: { type: MarkerType.ArrowClosed, color: "#7c5cfc" },
};

/**
 * Options for "related concept" edges: dashed, muted, no arrowhead.
 * Spread or assign per-edge to override the default prerequisite style.
 */
export const relatedEdgeOptions = {
  animated: false,
  style: relatedEdgeStyle,
  markerEnd: undefined,
};

// ─── MiniMap node color helper ────────────────────────────────────────────────
export function minimapNodeColor(mastery: number): string {
  return masteryColor(mastery);
}
