"use client";

import { use } from "react";
import { useSearchParams } from "next/navigation";
import { AlertCircle, Network, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";
import { useAuth } from "@/hooks/use-auth";
import { useCourseGraph, useCourseMastery } from "@/hooks/use-concepts";
import { ConceptHub } from "@/components/graph/ConceptHub";

// ─── Shared state-container ───────────────────────────────────────────────────

function StateContainer({
  children,
  role = "region",
  label,
}: {
  children: React.ReactNode;
  role?: "region" | "alert" | "status";
  label?: string;
}) {
  return (
    <motion.div
      className="flex flex-col items-center justify-center gap-6 rounded-xl py-16 text-center"
      style={{
        background: "#0a0a0f",
        backgroundImage: "radial-gradient(circle, #22223a 1px, transparent 1px)",
        backgroundSize: "28px 28px",
        border: "1px solid rgba(255,255,255,0.07)",
      }}
      role={role}
      aria-label={label}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.22 }}
    >
      {children}
    </motion.div>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function ConceptHubSkeleton() {
  return (
    <div
      className="mx-auto max-w-3xl space-y-4"
      role="status"
      aria-busy="true"
      aria-label="Loading concept hub…"
    >
      {/* Header card skeleton */}
      <div
        className="relative overflow-hidden rounded-xl p-6"
        style={{ background: "#14141f", border: "1px solid rgba(255,255,255,0.07)" }}
      >
        <div className="flex items-start gap-5">
          {/* Mastery ring placeholder */}
          <div
            className="size-24 shrink-0 rounded-full"
            style={{ background: "#1e1e2e" }}
            aria-hidden="true"
          />
          <div className="flex-1 space-y-3 pt-1">
            <div className="h-2.5 w-20 rounded-full" style={{ background: "#1e1e2e" }} />
            <div className="h-6 w-52 rounded-lg" style={{ background: "#1e1e2e" }} />
            <div className="h-3 w-full rounded-md" style={{ background: "#1e1e2e" }} />
            <div className="h-3 w-3/4 rounded-md" style={{ background: "#1e1e2e" }} />
            <div className="mt-4 h-9 w-36 rounded-lg" style={{ background: "#1e1e2e" }} />
          </div>
        </div>
        {/* Full-card shimmer sweep */}
        <div className="animate-shimmer pointer-events-none absolute inset-0" aria-hidden="true" />
      </div>

      {/* Section card skeletons — staggered heights mimic real content */}
      {([160, 120, 80] as const).map((h, i) => (
        <div
          key={i}
          className="relative overflow-hidden rounded-xl p-5"
          style={{ background: "#14141f", border: "1px solid rgba(255,255,255,0.07)" }}
          aria-hidden="true"
        >
          <div className="mb-3 h-3 w-28 rounded-full" style={{ background: "#1e1e2e" }} />
          <div
            className="rounded-lg"
            style={{ background: "#1e1e2e", height: h }}
          />
          <div className="animate-shimmer pointer-events-none absolute inset-0" />
        </div>
      ))}
    </div>
  );
}

// ─── Decorative error icon ────────────────────────────────────────────────────

function ErrorIcon() {
  return (
    <div className="relative flex items-center justify-center">
      <div
        className="absolute size-32 rounded-full"
        style={{ border: "1px dashed rgba(248, 113, 113, 0.12)", opacity: 0.7 }}
        aria-hidden="true"
      />
      <div
        className="absolute size-20 rounded-full"
        style={{ border: "1px solid rgba(248, 113, 113, 0.08)" }}
        aria-hidden="true"
      />
      <motion.div
        className="flex size-14 items-center justify-center rounded-full"
        style={{
          background: "rgba(248, 113, 113, 0.06)",
          border: "1px solid rgba(248, 113, 113, 0.22)",
        }}
        animate={{
          boxShadow: [
            "0 0 0px rgba(248, 113, 113, 0)",
            "0 0 20px rgba(248, 113, 113, 0.14)",
            "0 0 0px rgba(248, 113, 113, 0)",
          ],
        }}
        transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
      >
        <AlertCircle
          className="size-6"
          style={{ color: "#f87171" }}
          strokeWidth={1.5}
          aria-hidden="true"
        />
      </motion.div>
    </div>
  );
}

// ─── Retry button ─────────────────────────────────────────────────────────────

function RetryButton({ onClick }: { onClick: () => void }) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      className="flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-medium outline-none focus-visible:ring-2 focus-visible:ring-[#7c5cfc] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a0f]"
      style={{
        background: "#14141f",
        border: "1px solid rgba(255,255,255,0.08)",
        color: "#a0a0b0",
      }}
      whileHover={{
        scale: 1.02,
        borderColor: "rgba(255,255,255,0.14)",
        color: "#e2e2e8",
      }}
      whileTap={{ scale: 0.96 }}
      aria-label="Retry loading knowledge graph"
    >
      <RefreshCw className="size-3" aria-hidden="true" />
      Try again
    </motion.button>
  );
}

// ─── ConceptHubPage ───────────────────────────────────────────────────────────

interface ConceptPageProps {
  params: Promise<{ conceptId: string }>;
}

export default function ConceptHubPage({ params }: ConceptPageProps) {
  const { conceptId } = use(params);
  const searchParams = useSearchParams();
  const courseId = searchParams.get("courseId") ?? "";

  const { token, loading: authLoading } = useAuth();
  const {
    data: graph,
    isLoading: graphLoading,
    error: graphError,
    refetch: refetchGraph,
  } = useCourseGraph(token, courseId);
  const { data: mastery, isLoading: masteryLoading } = useCourseMastery(
    token,
    courseId,
  );

  // ── Loading ──
  if (authLoading || graphLoading || masteryLoading) {
    return <ConceptHubSkeleton />;
  }

  // ── Missing courseId context ──
  if (!courseId) {
    return (
      <div className="mx-auto max-w-3xl">
        <StateContainer role="region" label="Missing course context">
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
                border: "1px solid rgba(255,255,255,0.07)",
              }}
            >
              <Network
                className="size-6"
                style={{ color: "#6b6b80" }}
                strokeWidth={1.5}
                aria-hidden="true"
              />
            </div>
          </div>
          <div className="max-w-xs px-6">
            <p className="text-sm font-semibold" style={{ color: "#e2e2e8" }}>
              Missing course context
            </p>
            <p className="mt-1 text-xs leading-relaxed" style={{ color: "#6b6b80" }}>
              Navigate to a concept from the knowledge graph to open its hub.
            </p>
          </div>
        </StateContainer>
      </div>
    );
  }

  // ── Graph fetch error ──
  if (graphError || !graph) {
    return (
      <div className="mx-auto max-w-3xl">
        <StateContainer role="alert" label="Failed to load knowledge graph">
          <ErrorIcon />
          <div className="max-w-xs px-6">
            <p className="text-sm font-semibold" style={{ color: "#e2e2e8" }}>
              Something went wrong
            </p>
            <p className="mt-1 text-xs leading-relaxed" style={{ color: "#6b6b80" }}>
              Failed to load the knowledge graph. Check your connection and try again.
            </p>
          </div>
          <RetryButton onClick={() => void refetchGraph()} />
        </StateContainer>
      </div>
    );
  }

  // ── Concept not found ──
  const concept = graph.concepts.find((c) => c.id === conceptId);
  if (!concept) {
    return (
      <div className="mx-auto max-w-3xl">
        <StateContainer role="region" label="Concept not found">
          <div className="relative flex items-center justify-center">
            <motion.div
              className="absolute size-32 rounded-full"
              style={{ border: "1px dashed rgba(255,255,255,0.05)" }}
              animate={{ rotate: 360 }}
              transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
              aria-hidden="true"
            />
            <div
              className="absolute size-20 rounded-full"
              style={{ border: "1px solid rgba(255,255,255,0.04)" }}
              aria-hidden="true"
            />
            <div
              className="flex size-14 items-center justify-center rounded-full"
              style={{
                background: "#14141f",
                border: "1px solid rgba(255,255,255,0.07)",
              }}
            >
              <Network
                className="size-6"
                style={{ color: "#6b6b80" }}
                strokeWidth={1.5}
                aria-hidden="true"
              />
            </div>
          </div>
          <div className="max-w-xs px-6">
            <p className="text-sm font-semibold" style={{ color: "#a0a0b0" }}>
              Concept not found
            </p>
            <p className="mt-1 text-xs leading-relaxed" style={{ color: "#6b6b80" }}>
              This concept doesn&apos;t exist in the knowledge graph for this course.
            </p>
          </div>
        </StateContainer>
      </div>
    );
  }

  return (
    <ConceptHub
      concept={concept}
      allConcepts={graph.concepts}
      masteryItems={mastery?.items ?? []}
    />
  );
}
