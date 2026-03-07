"use client";

import { useMemo, useEffect, useRef, useCallback, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Zap,
  BookOpen,
  Users,
  CheckCircle2,
  Target,
  Network,
  AlertCircle,
  RefreshCw,
  ChevronUp,
  X,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { useActiveOrg } from "@/hooks/use-active-org";
import {
  useConceptMissions,
  useConceptTeamMastery,
} from "@/hooks/use-concept-hub";
import { useDueCount } from "@/hooks/use-flashcards";
import type { CourseGraphResponse, MasteryItem, ConceptData } from "@/lib/api";

// ─── Types ─────────────────────────────────────────────────────────────────────

type NodeRole = "prereq" | "dependent" | "related";

interface LayoutNode {
  concept: ConceptData;
  role: NodeRole;
  /** Degrees in SVG screen coords: 0=right, 90=down, 180=left, 270=up */
  angle: number;
  mastery: number;
}

export interface MindMapViewProps {
  /** ID of the concept to place at the center of the radial layout */
  conceptId: string;
  /** Full course graph passed from parent (no extra fetch needed) */
  graphData: CourseGraphResponse;
  /** Per-concept mastery items for the current user */
  masteryItems: MasteryItem[];
  /** Called when the user clicks "Back to Map" */
  onBack: () => void;
  /**
   * Called when the user clicks a surrounding node — lets the parent
   * switch the mind-map to a different concept without unmounting.
   */
  onNodeClick?: (conceptId: string) => void;
}

// ─── SVG layout constants ───────────────────────────────────────────────────────

const VW = 900;   // viewBox width
const VH = 540;   // viewBox height
const CX = VW / 2; // center X = 450
const CY = VH / 2; // center Y = 270

const ORBIT_R  = 205;  // pixels from center to surrounding node centres
const CENTER_R = 52;   // radius of the center concept circle
const NODE_R   = 30;   // radius of surrounding concept circles
const RING_PAD = 3;    // gap between circle edge and mastery ring

// ─── Role color palette ─────────────────────────────────────────────────────────

const ROLE_COLOR: Record<NodeRole | "center", string> = {
  center:    "#7c5cfc",
  prereq:    "#60a5fa",
  dependent: "#34d399",
  related:   "#9b80fd",
};

const ROLE_GLOW: Record<NodeRole | "center", string> = {
  center:    "rgba(124, 92, 252, 0.28)",
  prereq:    "rgba(96, 165, 250, 0.22)",
  dependent: "rgba(52, 211, 153, 0.22)",
  related:   "rgba(155, 128, 253, 0.18)",
};

const ROLE_LABEL: Record<NodeRole, string> = {
  prereq:    "Prerequisite",
  dependent: "Depends on this",
  related:   "Related",
};

// ─── Pure helpers ───────────────────────────────────────────────────────────────

function getMastery(conceptId: string, items: MasteryItem[]): number {
  const item = items.find((m) => m.concept_id === conceptId);
  return item ? Math.round(item.mastery * 100) : 0;
}

/**
 * Distribute `n` angles evenly, centered on `center` (degrees),
 * with a total arc of at most `maxSpread` degrees.
 */
function distributeAngles(n: number, center: number, maxSpread: number): number[] {
  if (n === 0) return [];
  if (n === 1) return [center];
  const spread = Math.min(maxSpread, (n - 1) * 42);
  return Array.from({ length: n }, (_, i) => center - spread / 2 + (i * spread) / (n - 1));
}

/** (angle°, radius) → SVG offset from origin */
function toXY(angleDeg: number, radius: number): { x: number; y: number } {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: radius * Math.cos(rad), y: radius * Math.sin(rad) };
}

/** Truncate label to `maxChars` for display inside a small circle */
function truncLabel(label: string, maxChars: number): string {
  return label.length > maxChars ? `${label.slice(0, maxChars - 1)}…` : label;
}

// ─── Radial layout computation ──────────────────────────────────────────────────

interface LayoutResult {
  centerConcept: ConceptData | null;
  centerMastery: number;
  nodes: LayoutNode[];
}

function computeLayout(
  conceptId: string,
  concepts: ConceptData[],
  masteryItems: MasteryItem[],
): LayoutResult {
  const center = concepts.find((c) => c.id === conceptId);
  if (!center) return { centerConcept: null, centerMastery: 0, nodes: [] };

  const centerMastery = getMastery(conceptId, masteryItems);

  // Prerequisites: direct prereqs of the selected concept
  const prereqIds = new Set(center.prerequisites);
  const prereqs = concepts.filter((c) => prereqIds.has(c.id));

  // Dependents: concepts that list the selected concept as a prereq
  const dependents = concepts.filter(
    (c) => c.prerequisites.includes(conceptId) && c.id !== conceptId,
  );

  // Related: same lesson first, then remaining (excluding above)
  const excludedIds = new Set([
    conceptId,
    ...prereqs.map((c) => c.id),
    ...dependents.map((c) => c.id),
  ]);
  const sameLesson = concepts.filter(
    (c) => !excludedIds.has(c.id) && c.lesson_id !== null && c.lesson_id === center.lesson_id,
  );
  const otherRelated = concepts.filter(
    (c) => !excludedIds.has(c.id) && (c.lesson_id === null || c.lesson_id !== center.lesson_id),
  );
  const related = [...sameLesson, ...otherRelated];

  // Cap to max 12 surrounding nodes, distributing budget fairly
  const maxP = Math.min(4, prereqs.length);
  const maxD = Math.min(4, dependents.length);
  const maxR = Math.min(12 - maxP - maxD, related.length);

  const trimP = prereqs.slice(0, maxP);
  const trimD = dependents.slice(0, maxD);
  const trimR = related.slice(0, maxR);

  // Angle assignment
  // Top arc (270° = up in SVG) for prerequisites
  const prereqAngles   = distributeAngles(trimP.length, 270, 110);
  // Bottom arc (90° = down) for dependents
  const depAngles      = distributeAngles(trimD.length, 90, 110);
  // Related: split left (180°) and right (0°)
  const leftCount      = Math.ceil(trimR.length / 2);
  const rightCount     = trimR.length - leftCount;
  const leftAngles     = distributeAngles(leftCount, 180, 80);
  const rightAngles    = distributeAngles(rightCount, 0, 80);
  const relatedAngles  = [...leftAngles, ...rightAngles];

  const nodes: LayoutNode[] = [
    ...trimP.map((c, i) => ({
      concept: c,
      role: "prereq" as NodeRole,
      angle: prereqAngles[i],
      mastery: getMastery(c.id, masteryItems),
    })),
    ...trimD.map((c, i) => ({
      concept: c,
      role: "dependent" as NodeRole,
      angle: depAngles[i],
      mastery: getMastery(c.id, masteryItems),
    })),
    ...trimR.map((c, i) => ({
      concept: c,
      role: "related" as NodeRole,
      angle: relatedAngles[i],
      mastery: getMastery(c.id, masteryItems),
    })),
  ];

  return { centerConcept: center, centerMastery, nodes };
}

// ─── Radial SVG Canvas ──────────────────────────────────────────────────────────

interface RadialCanvasProps {
  centerConcept: ConceptData;
  centerMastery: number;
  nodes: LayoutNode[];
  onNodeClick?: (conceptId: string) => void;
}

function RadialCanvas({ centerConcept, centerMastery, nodes, onNodeClick }: RadialCanvasProps) {
  // Center mastery ring geometry
  const cRingR  = CENTER_R - RING_PAD;
  const cCirc   = 2 * Math.PI * cRingR;
  const cOffset = cCirc * (1 - centerMastery / 100);

  return (
    <svg
      viewBox={`0 0 ${VW} ${VH}`}
      className="h-full w-full"
      style={{ overflow: "visible" }}
      aria-label={`Mind map centered on ${centerConcept.name}`}
      role="img"
    >
      {/* ── Filter definitions ── */}
      <defs>
        <filter id="glow-center" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="8" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="glow-node" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* ── All positioned relative to center (CX, CY) ── */}
      <g transform={`translate(${CX}, ${CY})`}>

        {/* ── Outer orbit ring — slow dashed rotation ── */}
        <motion.g
          animate={{ rotate: 360 }}
          transition={{ duration: 90, repeat: Infinity, ease: "linear" }}
          style={{ originX: "0px", originY: "0px" }}
          aria-hidden="true"
        >
          <circle
            cx="0" cy="0" r={ORBIT_R}
            fill="none"
            stroke="rgba(124, 92, 252, 0.07)"
            strokeWidth="1"
            strokeDasharray="3 14"
          />
        </motion.g>

        {/* ── Second decorative ring (static) ── */}
        <circle
          cx="0" cy="0" r={ORBIT_R * 0.52}
          fill="none"
          stroke="rgba(124, 92, 252, 0.05)"
          strokeWidth="1"
          aria-hidden="true"
        />

        {/* ── Edges: center node edge → satellite node edge ── */}
        {nodes.map((node, i) => {
          const color = ROLE_COLOR[node.role];
          // Start edge at the surface of the center circle
          const start = toXY(node.angle, CENTER_R + 5);
          // End edge at the near surface of the satellite circle
          const end   = toXY(node.angle, ORBIT_R - NODE_R - 4);
          return (
            <motion.path
              key={`edge-${node.concept.id}`}
              d={`M ${start.x} ${start.y} L ${end.x} ${end.y}`}
              stroke={color}
              strokeWidth={1.5}
              strokeOpacity={0.4}
              strokeLinecap="round"
              fill="none"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ delay: i * 0.045 + 0.08, duration: 0.45, ease: "easeOut" }}
            />
          );
        })}

        {/* ── Surrounding nodes ── */}
        {nodes.map((node, i) => {
          const { x, y } = toXY(node.angle, ORBIT_R);
          const color    = ROLE_COLOR[node.role];
          const glow     = ROLE_GLOW[node.role];
          const ringR    = NODE_R - RING_PAD;
          const circ     = 2 * Math.PI * ringR;
          const offset   = circ * (1 - node.mastery / 100);
          const label    = truncLabel(node.concept.name, 7);

          const isClickable = Boolean(onNodeClick);
          return (
            <motion.g
              key={node.concept.id}
              initial={{ x: 0, y: 0, opacity: 0, scale: 0.25 }}
              animate={{ x, y, opacity: 1, scale: 1 }}
              whileHover={isClickable ? { scale: 1.15 } : undefined}
              whileTap={isClickable ? { scale: 0.9 } : undefined}
              transition={{
                delay: i * 0.05 + 0.12,
                type: "spring",
                stiffness: 260,
                damping: 22,
              }}
              style={{ originX: "0px", originY: "0px", cursor: isClickable ? "pointer" : "default" }}
              aria-label={`${ROLE_LABEL[node.role]}: ${node.concept.name}, ${node.mastery}% mastery${isClickable ? ". Press Enter to open." : ""}`}
              role={isClickable ? "button" : "group"}
              tabIndex={isClickable ? 0 : undefined}
              onClick={isClickable ? () => onNodeClick?.(node.concept.id) : undefined}
              onKeyDown={isClickable ? (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onNodeClick?.(node.concept.id);
                }
              } : undefined}
            >
              {/* Native browser tooltip — full concept name on hover */}
              <title>{`${node.concept.name} · ${ROLE_LABEL[node.role]} · ${node.mastery}% mastery`}</title>

              {/* Aura */}
              <circle cx="0" cy="0" r={NODE_R + 6} fill={glow} />

              {/* Node body */}
              <circle
                cx="0" cy="0" r={NODE_R}
                fill="#14141f"
                stroke="#1e1e2e"
                strokeWidth="1.5"
              />

              {/* Mastery ring (track + fill), rotated to start at top */}
              <g transform="rotate(-90)">
                {/* Track */}
                <circle
                  cx="0" cy="0" r={ringR}
                  fill="none"
                  stroke="#22223a"
                  strokeWidth="2"
                />
                {/* Fill */}
                <motion.circle
                  cx="0" cy="0" r={ringR}
                  fill="none"
                  stroke={color}
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeDasharray={circ}
                  initial={{ strokeDashoffset: circ }}
                  animate={{ strokeDashoffset: offset }}
                  transition={{ delay: i * 0.05 + 0.38, duration: 0.75, ease: "easeOut" }}
                />
              </g>

              {/* Label */}
              <text
                x="0" y="3"
                textAnchor="middle"
                fill="#e2e2e8"
                fontSize="9"
                fontWeight="600"
                style={{ fontFamily: "var(--font-mono, ui-monospace, monospace)", pointerEvents: "none" }}
              >
                {label}
              </text>

              {/* Role color dot — top-right corner */}
              <circle cx={NODE_R - 7} cy={-(NODE_R - 7)} r="4" fill={color} />

              {/* Mastery % micro-badge */}
              <text
                x="0" y="15"
                textAnchor="middle"
                fill={color}
                fontSize="7"
                fontWeight="600"
                style={{ fontFamily: "var(--font-mono, ui-monospace, monospace)", pointerEvents: "none" }}
              >
                {node.mastery}%
              </text>
            </motion.g>
          );
        })}

        {/* ── Center node ── */}

        {/* Pulsing outer halo */}
        <motion.circle
          cx="0" cy="0" r={CENTER_R + 10}
          fill="rgba(124, 92, 252, 0.07)"
          animate={{
            r:       [CENTER_R + 8,  CENTER_R + 22, CENTER_R + 8],
            opacity: [0.7,            0.12,           0.7],
          }}
          transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
          aria-hidden="true"
        />

        {/* Inner glow ring */}
        <circle
          cx="0" cy="0" r={CENTER_R + 3}
          fill="rgba(124, 92, 252, 0.1)"
          aria-hidden="true"
        />

        {/* Body */}
        <motion.circle
          cx="0" cy="0" r={CENTER_R}
          fill="#14141f"
          stroke="#7c5cfc"
          strokeWidth="2"
          initial={{ scale: 0.4, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          style={{ originX: "0px", originY: "0px" }}
          filter="url(#glow-center)"
        />

        {/* Center mastery ring */}
        <g transform="rotate(-90)">
          {/* Track */}
          <circle
            cx="0" cy="0" r={cRingR}
            fill="none"
            stroke="#22223a"
            strokeWidth="3"
          />
          {/* Fill */}
          <motion.circle
            cx="0" cy="0" r={cRingR}
            fill="none"
            stroke="#7c5cfc"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={cCirc}
            initial={{ strokeDashoffset: cCirc }}
            animate={{ strokeDashoffset: cOffset }}
            transition={{ duration: 1.4, delay: 0.2, ease: "easeOut" }}
          />
        </g>

        {/* Native browser tooltip for center node */}
        <title>{`${centerConcept.name} · ${centerMastery}% mastery`}</title>

        {/* Center label — concept name (14 char limit for the larger circle) */}
        <motion.text
          x="0" y="-4"
          textAnchor="middle"
          fill="#e2e2e8"
          fontSize="11"
          fontWeight="600"
          style={{ fontFamily: "var(--font-sans, sans-serif)", pointerEvents: "none" }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.25 }}
        >
          {truncLabel(centerConcept.name, 14)}
        </motion.text>

        {/* Center mastery % */}
        <motion.text
          x="0" y="13"
          textAnchor="middle"
          fill="#7c5cfc"
          fontSize="10"
          fontWeight="600"
          style={{ fontFamily: "var(--font-mono, ui-monospace, monospace)", pointerEvents: "none" }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.2 }}
        >
          {centerMastery}%
        </motion.text>
      </g>

      {/* ── Empty state: isolated concept ── */}
      {nodes.length === 0 && (
        <g aria-live="polite">
          <text
            x={CX}
            y={CY + ORBIT_R * 0.72}
            textAnchor="middle"
            fill="#6b6b80"
            fontSize="11"
            style={{ fontFamily: "var(--font-mono, ui-monospace, monospace)" }}
          >
            No connected concepts
          </text>
          <text
            x={CX}
            y={CY + ORBIT_R * 0.72 + 17}
            textAnchor="middle"
            fill="#3a3a55"
            fontSize="9"
            style={{ fontFamily: "var(--font-mono, ui-monospace, monospace)" }}
          >
            This concept has no prerequisites, dependents, or related nodes
          </text>
        </g>
      )}

      {/* ── Legend — bottom-left (hidden when no nodes) ── */}
      {nodes.length > 0 && (
      <g transform={`translate(16, ${VH - 60})`} aria-label="Node role legend" role="group">
        {(
          [
            { role: "prereq",    label: "Prerequisites" },
            { role: "dependent", label: "Dependents" },
            { role: "related",   label: "Related" },
          ] as const
        ).map(({ role, label }, i) => (
          <g key={role} transform={`translate(0, ${i * 17})`}>
            <circle cx="5" cy="5" r="4.5" fill={ROLE_COLOR[role]} />
            <text
              x="15" y="9"
              fill="#6b6b80"
              fontSize="9"
              style={{ fontFamily: "var(--font-mono, ui-monospace, monospace)" }}
            >
              {label}
            </text>
          </g>
        ))}
      </g>
      )}
    </svg>
  );
}

// ─── StatBox ────────────────────────────────────────────────────────────────────

interface StatBoxProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
  /** When true, renders a skeleton placeholder instead of the value */
  loading?: boolean;
}

function StatBox({ icon, label, value, color, loading }: StatBoxProps) {
  return (
    <div
      className="flex flex-col items-center gap-1 rounded-xl py-3 text-center transition-colors duration-150 hover:bg-white/[0.03]"
      style={{
        background: "rgba(255,255,255,0.02)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <span style={{ color }}>{icon}</span>
      {loading ? (
        <Skeleton className="h-4 w-8 rounded" />
      ) : (
        <span
          className="text-base font-semibold"
          style={{ color: "#e2e2e8", fontFamily: "var(--font-mono, ui-monospace, monospace)" }}
        >
          {value}
        </span>
      )}
      <span className="text-[10px]" style={{ color: "#6b6b80" }}>
        {label}
      </span>
    </div>
  );
}

// ─── DetailPanel ────────────────────────────────────────────────────────────────

interface DetailPanelProps {
  concept: ConceptData;
  mastery: number;
}

function DetailPanel({ concept, mastery }: DetailPanelProps) {
  const { token, user } = useAuth();
  const { activeOrg }   = useActiveOrg();
  const isAdmin = user?.role === "admin" || user?.role === "teacher";

  const {
    data: missions,
    isLoading: missionsLoading,
    isError: missionsError,
    refetch: refetchMissions,
  } = useConceptMissions(token, concept.id);

  const { data: dueCount,    isLoading: dueLoading      } = useDueCount(token);
  const { data: teamMembers, isLoading: teamLoading     } = useConceptTeamMastery(
    token,
    activeOrg?.id ?? null,
    isAdmin,
  );

  const completed  = missions?.filter((m) => m.status === "completed") ?? [];
  const available  = missions?.filter((m) => m.status !== "completed") ?? [];
  const hasMission = available.length > 0;
  const hasCards   = (dueCount ?? 0) > 0;

  // Mastery ring
  const ringR     = 36;
  const ringCirc  = 2 * Math.PI * ringR;
  const ringOff   = ringCirc * (1 - mastery / 100);
  const masteryCol =
    mastery >= 80 ? "#34d399" :
    mastery >= 30 ? "#7c5cfc" :
    "#6b6b80";

  const top3Team = teamMembers?.slice(0, 3) ?? [];

  return (
    <ScrollArea className="h-full">
      <div className="space-y-5 p-5">

        {/* ── Concept name + description ── */}
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="flex items-center gap-1.5">
            <span
              className="rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-widest"
              style={{
                background: "rgba(124, 92, 252, 0.1)",
                border: "1px solid rgba(124, 92, 252, 0.18)",
                color: "#9b80fd",
              }}
            >
              Concept
            </span>
          </div>
          <h2 className="mt-2 text-xl font-semibold leading-snug" style={{ color: "#e2e2e8", letterSpacing: "-0.01em" }}>
            {concept.name}
          </h2>
          {concept.description && (
            <p className="mt-1.5 text-xs leading-relaxed" style={{ color: "#6b6b80" }}>
              {concept.description}
            </p>
          )}
        </motion.div>

        {/* ── Mastery ring ── */}
        <motion.div
          className="flex items-center gap-4"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.22, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          <svg
            width="88"
            height="88"
            viewBox="-44 -44 88 88"
            aria-label={`${mastery}% mastery`}
            role="img"
          >
            {/* Track */}
            <g transform="rotate(-90)">
              <circle cx="0" cy="0" r={ringR} fill="none" stroke="#22223a" strokeWidth="4" />
              <motion.circle
                cx="0" cy="0" r={ringR}
                fill="none"
                stroke={masteryCol}
                strokeWidth="4"
                strokeLinecap="round"
                strokeDasharray={ringCirc}
                initial={{ strokeDashoffset: ringCirc }}
                animate={{ strokeDashoffset: ringOff }}
                transition={{ duration: 1.2, ease: "easeOut" }}
              />
            </g>
            {/* Value */}
            <text
              x="0" y="-3"
              textAnchor="middle"
              fill={masteryCol}
              fontSize="18"
              fontWeight="600"
              style={{ fontFamily: "var(--font-mono, ui-monospace, monospace)" }}
            >
              {mastery}
            </text>
            <text
              x="0" y="12"
              textAnchor="middle"
              fill="#6b6b80"
              fontSize="9"
              style={{ fontFamily: "var(--font-mono, ui-monospace, monospace)" }}
            >
              %
            </text>
          </svg>

          <div className="space-y-1.5">
            <span
              className="inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold"
              style={{
                background: `${masteryCol}18`,
                border: `1px solid ${masteryCol}30`,
                color: masteryCol,
                fontFamily: "var(--font-mono, ui-monospace, monospace)",
              }}
            >
              {mastery >= 80 ? "Mastered" : mastery >= 30 ? "In Progress" : "Not Started"}
            </span>
            <p className="text-xs" style={{ color: "#6b6b80" }}>
              {mastery >= 80
                ? "Ready to teach others"
                : mastery > 0
                  ? `${80 - mastery}% remaining to mastery`
                  : "Start a mission to begin"}
            </p>
          </div>
        </motion.div>

        {/* ── Divider ── */}
        <div
          aria-hidden="true"
          style={{ height: 1, background: "rgba(255,255,255,0.06)", margin: "0 -4px" }}
        />

        {/* ── Stats row — or missions error banner ── */}
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.28, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          {missionsError ? (
            /* ── Partial/degraded: missions API failed, show inline recovery ── */
            <div
              className="flex items-center justify-between rounded-xl px-3 py-2.5"
              style={{
                background: "rgba(248, 113, 113, 0.06)",
                border: "1px solid rgba(248, 113, 113, 0.14)",
              }}
              role="alert"
            >
              <div className="flex items-center gap-1.5">
                <AlertCircle className="size-3.5 shrink-0" style={{ color: "#f87171" }} aria-hidden="true" />
                <span className="text-xs" style={{ color: "#f87171" }}>
                  Mission data unavailable
                </span>
              </div>
              <motion.button
                type="button"
                onClick={() => void refetchMissions()}
                className="flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-medium outline-none focus-visible:ring-1 focus-visible:ring-[#7c5cfc] transition-colors duration-150"
                style={{
                  background: "rgba(248, 113, 113, 0.1)",
                  color: "#f87171",
                }}
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.96 }}
                aria-label="Retry loading mission data"
              >
                <RefreshCw className="size-2.5" aria-hidden="true" />
                Retry
              </motion.button>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              <StatBox
                icon={<CheckCircle2 className="size-3.5" aria-hidden="true" />}
                label="Done"
                value={String(completed.length)}
                color="#34d399"
                loading={missionsLoading}
              />
              <StatBox
                icon={<BookOpen className="size-3.5" aria-hidden="true" />}
                label="Due cards"
                value={String(dueCount ?? 0)}
                color="#60a5fa"
                loading={dueLoading}
              />
              <StatBox
                icon={<Target className="size-3.5" aria-hidden="true" />}
                label="Available"
                value={String(available.length)}
                color="#9b80fd"
                loading={missionsLoading}
              />
            </div>
          )}
        </motion.div>

        {/* ── Primary CTA: Start Mission ── */}
        {!missionsError && mastery < 80 && hasMission && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <Link href={`/missions/${available[0].id}`} className="block">
              <motion.button
                type="button"
                className="w-full rounded-xl px-4 py-3 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-[#7c5cfc] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a0f]"
                style={{
                  background: "linear-gradient(135deg, #7c5cfc 0%, #6b4fe0 100%)",
                  boxShadow: "0 2px 16px rgba(124, 92, 252, 0.25)",
                }}
                whileHover={{ boxShadow: "0 4px 28px rgba(124, 92, 252, 0.45)", scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
                transition={{ duration: 0.15 }}
              >
                <span className="flex items-center justify-center gap-2">
                  <Zap className="size-4" aria-hidden="true" />
                  Start Mission
                </span>
              </motion.button>
            </Link>
          </motion.div>
        )}

        {/* ── Empty missions nudge — not loading, no error, but nothing available ── */}
        {!missionsLoading && !missionsError && !hasMission && mastery < 80 && (
          <motion.div
            className="rounded-xl px-3 py-3 text-center"
            style={{
              background: "rgba(124, 92, 252, 0.04)",
              border: "1px dashed rgba(124, 92, 252, 0.18)",
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.38 }}
          >
            <p className="text-xs" style={{ color: "#6b6b80" }}>
              No missions available yet.{" "}
              <span style={{ color: "#9b80fd" }}>Missions are generated as you explore.</span>
            </p>
          </motion.div>
        )}

        {/* ── Secondary: Review Flashcards ── */}
        {hasCards && (
          <Link href="/flashcards" className="block">
            <motion.button
              type="button"
              className="w-full rounded-xl px-4 py-2.5 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-[#7c5cfc]"
              style={{
                background: "transparent",
                border: "1px solid rgba(255,255,255,0.08)",
                color: "#9b80fd",
              }}
              whileHover={{
                borderColor: "rgba(155, 128, 253, 0.35)",
                scale: 1.01,
                background: "rgba(124, 92, 252, 0.05)",
              }}
              whileTap={{ scale: 0.98 }}
              transition={{ duration: 0.15 }}
            >
              <span className="flex items-center justify-center gap-2">
                <BookOpen className="size-3.5" aria-hidden="true" />
                Review {dueCount} flashcard{dueCount !== 1 ? "s" : ""}
              </span>
            </motion.button>
          </Link>
        )}

        {/* ── Team members (admin only) ── */}
        {isAdmin && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.42, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="mb-3 flex items-center gap-1.5">
              <Users className="size-3.5" style={{ color: "#6b6b80" }} aria-hidden="true" />
              <p
                className="text-[10px] font-semibold uppercase tracking-widest"
                style={{ color: "#6b6b80" }}
              >
                Team
              </p>
            </div>

            {teamLoading ? (
              <div className="space-y-2.5">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-2.5">
                    <Skeleton className="size-7 rounded-full" />
                    <div className="flex-1 space-y-1.5">
                      <Skeleton className="h-2.5 w-24" />
                      <Skeleton className="h-1.5 w-full" />
                    </div>
                  </div>
                ))}
              </div>
            ) : top3Team.length === 0 ? (
              <p className="text-xs" style={{ color: "#6b6b80" }}>
                No team data available
              </p>
            ) : (
              <div className="space-y-3">
                {top3Team.map((member) => {
                  const pct      = Math.min(100, Math.round((member.level / 5) * 100));
                  const initials = member.user_id.slice(0, 2).toUpperCase();
                  const col      = pct >= 80 ? "#34d399" : pct >= 30 ? "#7c5cfc" : "#6b6b80";

                  return (
                    <div key={member.user_id} className="flex items-center gap-2.5">
                      <Avatar className="size-7 shrink-0">
                        <AvatarFallback
                          className="text-[10px] font-bold"
                          style={{
                            background: "rgba(124, 92, 252, 0.12)",
                            color: "#9b80fd",
                          }}
                        >
                          {initials}
                        </AvatarFallback>
                      </Avatar>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-1">
                          <span
                            className="truncate text-[11px]"
                            style={{ color: "#a0a0b0" }}
                          >
                            {member.user_id.slice(0, 8)}
                          </span>
                          <span
                            className="shrink-0 text-[10px] font-semibold"
                            style={{
                              color: col,
                              fontFamily: "var(--font-mono, ui-monospace, monospace)",
                            }}
                          >
                            {pct}%
                          </span>
                        </div>
                        <div
                          className="mt-1 h-1 w-full overflow-hidden rounded-full"
                          style={{ background: "rgba(255,255,255,0.05)" }}
                        >
                          <motion.div
                            className="h-full rounded-full"
                            style={{ background: col }}
                            initial={{ width: 0 }}
                            animate={{ width: `${pct}%` }}
                            transition={{ duration: 0.6, ease: "easeOut", delay: 0.2 }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </motion.div>
        )}

      </div>
    </ScrollArea>
  );
}

// ─── MindMapView ────────────────────────────────────────────────────────────────

export function MindMapView({
  conceptId,
  graphData,
  masteryItems,
  onBack,
  onNodeClick,
}: MindMapViewProps) {
  // Mobile panel toggle — shown only on screens narrower than lg breakpoint.
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false);

  const { centerConcept, centerMastery, nodes } = useMemo(
    () => computeLayout(conceptId, graphData.concepts, masteryItems),
    [conceptId, graphData, masteryItems],
  );

  // Keyboard: Escape → back
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onBack();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onBack]);

  // Focus the back button on mount for keyboard users
  const backBtnRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    backBtnRef.current?.focus();
  }, []);

  const handleNodeClick = useCallback(
    (id: string) => onNodeClick?.(id),
    [onNodeClick],
  );

  if (!centerConcept) {
    return (
      <div
        className="flex h-full items-center justify-center"
        style={{
          background: "#07070b",
          backgroundImage: "radial-gradient(circle, #22223a 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      >
        <motion.div
          className="flex flex-col items-center gap-4 text-center"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          {/* Decorative rings */}
          <div className="relative flex items-center justify-center">
            <div
              className="absolute size-24 rounded-full"
              style={{ border: "1px dashed rgba(255,255,255,0.06)" }}
              aria-hidden="true"
            />
            <div
              className="flex size-14 items-center justify-center rounded-full"
              style={{
                background: "#14141f",
                border: "1px solid rgba(255,255,255,0.08)",
              }}
            >
              <Network
                className="size-5"
                style={{ color: "#6b6b80" }}
                strokeWidth={1.5}
                aria-hidden="true"
              />
            </div>
          </div>

          <div>
            <p className="text-sm font-semibold" style={{ color: "#a0a0b0" }}>
              Concept not found
            </p>
            <p className="mt-1 text-xs" style={{ color: "#6b6b80" }}>
              This concept doesn&apos;t exist in the graph
            </p>
          </div>

          <motion.button
            type="button"
            onClick={onBack}
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium outline-none focus-visible:ring-2 focus-visible:ring-[#7c5cfc] transition-colors duration-150"
            style={{
              background: "#14141f",
              border: "1px solid rgba(255,255,255,0.08)",
              color: "#a0a0b0",
            }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.96 }}
          >
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            Back to Map
          </motion.button>
        </motion.div>
      </div>
    );
  }

  return (
    <div
      className="flex h-full overflow-hidden"
      style={{ background: "#07070b" }}
    >
      {/* ── Left: SVG radial canvas ── */}
      <div className="relative min-h-0 flex-1 overflow-hidden">
        {/* Dot-grid texture */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage: "radial-gradient(circle, #22223a 1px, transparent 1px)",
            backgroundSize: "28px 28px",
            opacity: 0.3,
          }}
          aria-hidden="true"
        />

        {/* Subtle vignette to anchor center visually */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse 65% 65% at 50% 50%, transparent 40%, rgba(7,7,11,0.6) 100%)",
          }}
          aria-hidden="true"
        />

        {/* Back to Map button — top-left */}
        <motion.button
          ref={backBtnRef}
          type="button"
          onClick={onBack}
          className="absolute left-4 top-4 z-10 flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium outline-none focus-visible:ring-2 focus-visible:ring-[#7c5cfc]"
          style={{
            background: "rgba(10, 10, 15, 0.88)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)",
            color: "#a0a0b0",
          }}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          whileHover={{
            scale: 1.03,
            borderColor: "rgba(124, 92, 252, 0.35)",
            color: "#e2e2e8",
          }}
          whileTap={{ scale: 0.97 }}
          aria-label="Back to concept map (Escape)"
        >
          <ArrowLeft className="size-3.5" aria-hidden="true" />
          Back to Map
          <span
            className="ml-1 rounded px-1 py-0.5 text-[9px]"
            style={{
              background: "rgba(255,255,255,0.06)",
              color: "#6b6b80",
              fontFamily: "var(--font-mono, ui-monospace, monospace)",
            }}
            aria-hidden="true"
          >
            esc
          </span>
        </motion.button>

        {/* Concept type badge — top-center */}
        <motion.div
          className="absolute left-1/2 top-4 z-10 -translate-x-1/2 rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-widest"
          style={{
            background: "rgba(124, 92, 252, 0.12)",
            border: "1px solid rgba(124, 92, 252, 0.2)",
            color: "#9b80fd",
          }}
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.25 }}
        >
          Mind Map — {nodes.length} related concept{nodes.length !== 1 ? "s" : ""}
        </motion.div>

        {/* SVG canvas */}
        <RadialCanvas
          centerConcept={centerConcept}
          centerMastery={centerMastery}
          nodes={nodes}
          onNodeClick={onNodeClick ? handleNodeClick : undefined}
        />
      </div>

      {/* ── Right: Detail panel (320px, re-mounts per concept for animation replay) ── */}
      {/* Hidden on < lg screens; mobile users get the slide-up panel instead.        */}
      <motion.aside
        key={centerConcept.id}
        className="hidden h-full shrink-0 overflow-hidden lg:flex lg:flex-col"
        style={{
          width: 320,
          background: "#0a0a0f",
          borderLeft: "1px solid rgba(255, 255, 255, 0.07)",
        }}
        initial={{ x: 40, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.38, ease: [0.16, 1, 0.3, 1] }}
        aria-label={`Details for ${centerConcept.name}`}
      >
        <DetailPanel concept={centerConcept} mastery={centerMastery} />
      </motion.aside>

      {/* ── Mobile concept info bar (visible only on < lg) ── */}
      {/* Sits at the bottom of the canvas and opens a slide-up panel.              */}
      <div className="lg:hidden">
        {/* Compact bottom pill — always visible on mobile */}
        <motion.button
          type="button"
          onClick={() => setMobileDetailOpen(true)}
          className="absolute inset-x-3 bottom-3 z-10 flex items-center justify-between rounded-xl px-4 py-3 outline-none focus-visible:ring-2 focus-visible:ring-[#7c5cfc]"
          style={{
            background: "rgba(10, 10, 15, 0.90)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            backdropFilter: "blur(14px)",
            WebkitBackdropFilter: "blur(14px)",
          }}
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.18, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          aria-label={`Open details for ${centerConcept.name}`}
          whileHover={{ borderColor: "rgba(124, 92, 252, 0.25)" }}
          whileTap={{ scale: 0.98 }}
        >
          <div className="min-w-0">
            <p
              className="truncate text-sm font-semibold"
              style={{ color: "#e2e2e8" }}
            >
              {centerConcept.name}
            </p>
            <p
              className="mt-0.5 text-[11px]"
              style={{
                color:
                  centerMastery >= 80
                    ? "#34d399"
                    : centerMastery >= 30
                      ? "#7c5cfc"
                      : "#6b6b80",
                fontFamily: "var(--font-mono, ui-monospace, monospace)",
              }}
            >
              {centerMastery}%
              {" · "}
              {centerMastery >= 80
                ? "Mastered"
                : centerMastery >= 30
                  ? "In progress"
                  : "Not started"}
            </p>
          </div>
          <ChevronUp
            className="ml-3 size-4 shrink-0"
            style={{ color: "#6b6b80" }}
            aria-hidden="true"
          />
        </motion.button>

        {/* Slide-up detail sheet — covers most of the screen on mobile */}
        <AnimatePresence>
          {mobileDetailOpen && (
            <>
              {/* Backdrop */}
              <motion.div
                key="mobile-backdrop"
                className="absolute inset-0 z-20"
                style={{ background: "rgba(7, 7, 11, 0.7)" }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                onClick={() => setMobileDetailOpen(false)}
                aria-hidden="true"
              />

              {/* Sheet */}
              <motion.div
                key="mobile-sheet"
                className="absolute inset-x-0 bottom-0 z-30 overflow-hidden rounded-t-2xl"
                style={{
                  background: "#0a0a0f",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                  maxHeight: "72vh",
                }}
                initial={{ y: "100%" }}
                animate={{ y: 0 }}
                exit={{ y: "100%" }}
                transition={{ type: "spring", stiffness: 340, damping: 36 }}
                aria-label={`Details for ${centerConcept.name}`}
                role="dialog"
                aria-modal="true"
              >
                {/* Sheet handle + close button */}
                <div
                  className="flex items-center justify-between px-5 pb-2 pt-4"
                  style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
                >
                  {/* Drag handle */}
                  <div
                    className="mx-auto h-1 w-10 rounded-full"
                    style={{ background: "rgba(255,255,255,0.12)" }}
                    aria-hidden="true"
                  />
                  <motion.button
                    type="button"
                    onClick={() => setMobileDetailOpen(false)}
                    className="absolute right-4 top-3.5 flex size-7 items-center justify-center rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-[#7c5cfc]"
                    style={{
                      background: "rgba(255,255,255,0.05)",
                      border: "1px solid rgba(255,255,255,0.08)",
                      color: "#6b6b80",
                    }}
                    whileHover={{ color: "#e2e2e8" }}
                    whileTap={{ scale: 0.9 }}
                    aria-label="Close details panel"
                  >
                    <X className="size-3.5" aria-hidden="true" />
                  </motion.button>
                </div>

                {/* Scrollable content — reuses the same DetailPanel */}
                <div style={{ height: "calc(72vh - 52px)" }}>
                  <DetailPanel concept={centerConcept} mastery={centerMastery} />
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
