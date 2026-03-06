"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { motion } from "framer-motion";
import { masteryColor } from "./graphTheme";

// ─── Node data type ───────────────────────────────────────────────────────────

export interface ConceptNodeData extends Record<string, unknown> {
  /** Display label shown inside the node */
  label: string;
  /** Mastery percentage 0–100 */
  mastery: number;
  /** Relative visual weight 0–1; larger values render bigger nodes */
  importance: number;
}

export type ConceptNodeType = Node<ConceptNodeData, "conceptNode">;

// ─── Size helpers ─────────────────────────────────────────────────────────────

/** Node diameter: 44px (unimportant) → 84px (very important) */
function nodeSize(importance: number): number {
  return Math.round(44 + importance * 40);
}

/** Label font size scales with node size */
function labelFontSize(importance: number): number {
  return Math.round(9 + importance * 5);
}

// ─── ConceptNode ──────────────────────────────────────────────────────────────

export const ConceptNode = memo(function ConceptNode({
  data,
  selected,
}: NodeProps<ConceptNodeType>) {
  const mastery = data.mastery ?? 0;
  const importance = Math.min(1, Math.max(0, data.importance ?? 0.5));
  const label = data.label ?? "";

  const color = masteryColor(mastery);
  const size = nodeSize(importance);
  const fontSize = labelFontSize(importance);

  // SVG mastery ring geometry
  const ringPadding = 3;
  const ringRadius = size / 2 - ringPadding;
  const circumference = 2 * Math.PI * ringRadius;
  const strokeDashoffset = circumference * (1 - mastery / 100);

  const truncatedLabel =
    label.length > 14 ? `${label.slice(0, 12)}…` : label;

  return (
    <motion.div
      style={{ width: size, height: size, position: "relative" }}
      whileHover={{ scale: 1.1 }}
      animate={{
        boxShadow: selected
          ? `0 0 20px ${color}60, 0 0 40px ${color}20`
          : "none",
      }}
      transition={{ duration: 0.15, ease: "easeOut" }}
    >
      {/* ── Circular node body ── */}
      <div
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          backgroundColor: "#14141f",
          border: selected ? `2px solid ${color}` : "1px solid #1e1e2e",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          overflow: "visible",
          transition: "border-color 0.2s ease",
        }}
      >
        {/* ── Mastery progress ring (SVG overlay) ── */}
        <svg
          width={size}
          height={size}
          style={{
            position: "absolute",
            inset: 0,
            // rotate so arc starts from 12-o'clock position
            transform: "rotate(-90deg)",
            pointerEvents: "none",
          }}
          aria-hidden="true"
        >
          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={ringRadius}
            fill="none"
            stroke="#22223a"
            strokeWidth={2}
          />
          {/* Progress arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={ringRadius}
            fill="none"
            stroke={color}
            strokeWidth={2}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            style={{ transition: "stroke-dashoffset 0.5s ease, stroke 0.3s ease" }}
          />
        </svg>

        {/* ── Concept label ── */}
        <span
          style={{
            fontSize,
            color: "#e2e2e8",
            fontWeight: 600,
            textAlign: "center",
            lineHeight: 1.25,
            padding: "0 8px",
            maxWidth: size - 16,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            pointerEvents: "none",
            zIndex: 1,
            position: "relative",
          }}
          title={label}
        >
          {truncatedLabel}
        </span>

        {/* ── Mastery percentage badge ── */}
        <div
          style={{
            position: "absolute",
            bottom: -9,
            right: -6,
            backgroundColor: color,
            color: mastery >= 30 ? "#ffffff" : "#0a0a0f",
            fontSize: 9,
            fontWeight: 700,
            borderRadius: 4,
            padding: "1px 4px",
            lineHeight: 1.5,
            fontFamily: "var(--font-mono, ui-monospace, monospace)",
            border: "1px solid #0a0a0f",
            zIndex: 2,
            pointerEvents: "none",
            transition: "background-color 0.3s ease",
          }}
          aria-label={`${mastery}% mastery`}
        >
          {mastery}%
        </div>
      </div>

      {/* ── React Flow connection handles (invisible, structural) ── */}
      <Handle
        type="target"
        position={Position.Top}
        style={{ opacity: 0, top: 0 }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ opacity: 0, bottom: 0 }}
      />
    </motion.div>
  );
});
