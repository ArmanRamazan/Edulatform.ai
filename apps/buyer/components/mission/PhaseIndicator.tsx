"use client";

import { cn } from "@/lib/utils";
import type { CoachPhase } from "@/lib/api";

const PHASES: { key: CoachPhase; label: string }[] = [
  { key: "recap", label: "Recap" },
  { key: "reading", label: "Reading" },
  { key: "questions", label: "Questions" },
  { key: "code_case", label: "Code" },
  { key: "wrap_up", label: "Wrap-up" },
];

interface PhaseIndicatorProps {
  currentPhase: CoachPhase;
  completedPhases: Set<CoachPhase>;
}

export function PhaseIndicator({ currentPhase, completedPhases }: PhaseIndicatorProps) {
  const currentIndex = PHASES.findIndex((p) => p.key === currentPhase);

  return (
    <div className="flex items-center gap-2">
      {PHASES.map((phase, i) => {
        const isCurrent = phase.key === currentPhase;
        const isCompleted = completedPhases.has(phase.key);

        return (
          <div key={phase.key} className="flex items-center gap-2">
            {i > 0 && (
              <div
                className={cn(
                  "h-px w-6 transition-colors duration-300",
                  i <= currentIndex ? "bg-primary" : "bg-border",
                )}
              />
            )}
            <div className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  "flex size-7 items-center justify-center rounded-full text-xs font-medium transition-all duration-300",
                  isCurrent && "scale-110 bg-primary text-primary-foreground ring-2 ring-primary/30",
                  isCompleted && !isCurrent && "bg-emerald-500 text-white",
                  !isCurrent && !isCompleted && "bg-secondary text-muted-foreground",
                )}
              >
                {isCompleted && !isCurrent ? (
                  <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>
              <span
                className={cn(
                  "text-[10px] font-medium transition-colors duration-300",
                  isCurrent ? "text-primary" : "text-muted-foreground",
                )}
              >
                {phase.label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
