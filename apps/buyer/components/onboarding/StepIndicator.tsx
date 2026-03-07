"use client";

import React from "react";
import { Check } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

export const ONBOARDING_STEP_LABELS = [
  "Organization",
  "Experience",
  "Assessment",
  "Plan",
  "Start",
] as const;

export const ONBOARDING_TOTAL_STEPS = ONBOARDING_STEP_LABELS.length;

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface StepIndicatorProps {
  currentStep: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export function StepIndicator({ currentStep }: StepIndicatorProps) {
  // Progress bar fills proportionally: step 1 = 0%, step 5 = 100%
  const progressPct =
    ((currentStep - 1) / (ONBOARDING_TOTAL_STEPS - 1)) * 100;

  return (
    <div
      className="w-full"
      role="progressbar"
      aria-valuenow={currentStep}
      aria-valuemin={1}
      aria-valuemax={ONBOARDING_TOTAL_STEPS}
      aria-label={`Step ${currentStep} of ${ONBOARDING_TOTAL_STEPS}: ${ONBOARDING_STEP_LABELS[currentStep - 1]}`}
    >
      {/* ── Circles + connector lines ── */}
      <div className="flex w-full items-center">
        {ONBOARDING_STEP_LABELS.map((label, index) => {
          const stepNumber = index + 1;
          const isCompleted = stepNumber < currentStep;
          const isActive = stepNumber === currentStep;
          const isUpcoming = stepNumber > currentStep;

          return (
            <React.Fragment key={label}>
              {/* Circle */}
              <div className="flex shrink-0 flex-col items-center gap-1.5">
                <motion.div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full border-2",
                    "text-xs font-semibold transition-colors duration-300",
                    isCompleted &&
                      "border-success bg-success text-white",
                    isActive &&
                      "border-primary bg-primary text-white",
                    isUpcoming &&
                      "border-border bg-background text-muted-foreground",
                  )}
                  // Pulse ring only on the active circle
                  animate={
                    isActive
                      ? {
                          boxShadow: [
                            "0 0 0 0px rgba(124,92,252,0.45)",
                            "0 0 0 7px rgba(124,92,252,0.07)",
                            "0 0 0 0px rgba(124,92,252,0.45)",
                          ],
                        }
                      : { boxShadow: "0 0 0 0px rgba(124,92,252,0)" }
                  }
                  transition={{
                    duration: 2.2,
                    repeat: isActive ? Infinity : 0,
                    ease: "easeInOut",
                  }}
                  initial={false}
                >
                  {isCompleted ? (
                    <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                  ) : (
                    <span>{stepNumber}</span>
                  )}
                </motion.div>

                {/* Label — hidden on mobile, shown on sm+ */}
                <span
                  className={cn(
                    "hidden text-[10px] font-medium leading-none sm:block",
                    isActive
                      ? "text-primary"
                      : "text-muted-foreground",
                  )}
                >
                  {label}
                </span>
              </div>

              {/* Connector line (not after the last step) */}
              {index < ONBOARDING_TOTAL_STEPS - 1 && (
                <div className="relative mx-1 h-px flex-1">
                  {/* Base track */}
                  <div className="absolute inset-0 bg-border" />
                  {/* Filled portion — slides in when step is completed */}
                  <motion.div
                    className="absolute inset-y-0 left-0"
                    style={{
                      background:
                        "linear-gradient(90deg, var(--primary), #a78bfa)",
                      boxShadow: "0 0 4px rgba(124,92,252,0.55)",
                    }}
                    animate={{
                      width: stepNumber < currentStep ? "100%" : "0%",
                    }}
                    transition={{ duration: 0.4, ease: "easeInOut" }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* ── Thin overall progress bar ── */}
      <div className="mt-4 h-0.5 w-full overflow-hidden rounded-full bg-border">
        <motion.div
          className="h-full rounded-full"
          style={{
            background:
              "linear-gradient(90deg, var(--primary) 0%, #a78bfa 100%)",
            boxShadow: "0 0 6px rgba(124,92,252,0.4)",
          }}
          animate={{ width: `${progressPct}%` }}
          transition={{ duration: 0.5, ease: "easeInOut" }}
        />
      </div>
    </div>
  );
}
