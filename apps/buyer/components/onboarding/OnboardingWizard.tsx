"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StepIndicator, ONBOARDING_TOTAL_STEPS } from "./StepIndicator";
import { StepOrganization } from "./steps/StepOrganization";
import { StepExperience } from "./steps/StepExperience";
import { StepAssessment } from "./steps/StepAssessment";
import { StepPlan } from "./steps/StepPlan";
import { StepStart } from "./steps/StepStart";

// ─────────────────────────────────────────────────────────────────────────────
// Types — exported so step components can import them
// ─────────────────────────────────────────────────────────────────────────────

export interface WizardData {
  orgName: string;
  orgSize: string | null;
  industry: string | null;
  experience: string | null;
  skills: string[];
  goal: string | null;
}

export interface StepProps {
  onNext: () => void;
  onBack: () => void;
  data: WizardData;
  setData: (data: WizardData) => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const STORAGE_KEY = "onboarding_wizard_step";

const INITIAL_DATA: WizardData = {
  orgName: "",
  orgSize: null,
  industry: null,
  experience: null,
  skills: [],
  goal: null,
};

// Slide variants: direction > 0 = forward, < 0 = backward
const stepVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 32 : -32,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction > 0 ? -32 : 32,
    opacity: 0,
  }),
};

// ─────────────────────────────────────────────────────────────────────────────
// Validation — which steps require something before "Continue"
// ─────────────────────────────────────────────────────────────────────────────

function isStepValid(step: number, data: WizardData): boolean {
  switch (step) {
    case 1:
      return data.orgName.trim().length > 0;
    case 2:
      return data.experience !== null;
    case 3:
      return data.skills.length > 0;
    case 4:
      return data.goal !== null;
    case 5:
      return true; // StepStart manages its own CTAs
    default:
      return false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export function OnboardingWizard() {
  // ── State ──────────────────────────────────────────────────────────────────

  // Start at step 1; restore from localStorage after mount (avoids SSR mismatch)
  const [currentStep, setCurrentStep] = useState(1);
  const [direction, setDirection] = useState(1);
  const [data, setData] = useState<WizardData>(INITIAL_DATA);

  // Focus management: step content is focused after each transition for
  // keyboard / screen-reader users
  const stepContentRef = useRef<HTMLDivElement>(null);

  // ── localStorage persistence ───────────────────────────────────────────────

  // Restore saved step on first render
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    const parsed = stored ? parseInt(stored, 10) : 1;
    if (!isNaN(parsed) && parsed >= 1 && parsed <= ONBOARDING_TOTAL_STEPS) {
      setCurrentStep(parsed);
    }
  }, []);

  // Persist whenever step changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(currentStep));
  }, [currentStep]);

  // Clear storage when wizard completes (step 5 reached)
  useEffect(() => {
    if (currentStep === ONBOARDING_TOTAL_STEPS) {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [currentStep]);

  // ── Focus on step change ───────────────────────────────────────────────────

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      stepContentRef.current?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(id);
  }, [currentStep]);

  // ── Navigation ─────────────────────────────────────────────────────────────

  const goNext = useCallback(() => {
    setDirection(1);
    setCurrentStep((s) => Math.min(s + 1, ONBOARDING_TOTAL_STEPS));
  }, []);

  const goBack = useCallback(() => {
    setDirection(-1);
    setCurrentStep((s) => Math.max(s - 1, 1));
  }, []);

  // ── Keyboard shortcuts ─────────────────────────────────────────────────────

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Enter to advance (only if valid and not on the final step)
      if (
        e.key === "Enter" &&
        currentStep < ONBOARDING_TOTAL_STEPS &&
        isStepValid(currentStep, data) &&
        // Do not intercept Enter inside text inputs
        (e.target as HTMLElement).tagName !== "INPUT" &&
        (e.target as HTMLElement).tagName !== "TEXTAREA"
      ) {
        goNext();
      }
      // Escape to go back
      if (e.key === "Escape" && currentStep > 1) {
        goBack();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [currentStep, data, goNext, goBack]);

  // ── Step props factory ─────────────────────────────────────────────────────

  const stepProps: StepProps = {
    onNext: goNext,
    onBack: goBack,
    data,
    setData,
  };

  const isLastStep = currentStep === ONBOARDING_TOTAL_STEPS;
  const canAdvance = isStepValid(currentStep, data);

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <>
      {/* Ambient background glow — rendered once, behind everything */}
      <div
        className="pointer-events-none fixed inset-0 -z-10"
        aria-hidden="true"
      >
        <div className="absolute left-1/2 top-1/3 h-[500px] w-[700px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/5 blur-3xl" />
        <div className="absolute bottom-1/4 right-1/3 h-[280px] w-[380px] rounded-full bg-info/5 blur-3xl" />
      </div>

      <div className="flex min-h-full flex-col items-center justify-center">
          <div className="w-full max-w-2xl py-8">
          {/* ── Step indicator ── */}
          <div className="mb-8">
            <StepIndicator currentStep={currentStep} />
          </div>

            {/* ── Screen-reader live region ── */}
          <div aria-live="polite" aria-atomic="true" className="sr-only">
            Step {currentStep} of {ONBOARDING_TOTAL_STEPS}
          </div>

          {/* ── Animated step content ── */}
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={currentStep}
              ref={stepContentRef}
              tabIndex={-1}
              custom={direction}
              variants={stepVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.22, ease: "easeOut" }}
              className="outline-none"
            >
              {currentStep === 1 && <StepOrganization {...stepProps} />}
              {currentStep === 2 && <StepExperience {...stepProps} />}
              {currentStep === 3 && <StepAssessment {...stepProps} />}
              {currentStep === 4 && <StepPlan {...stepProps} />}
              {currentStep === 5 && <StepStart {...stepProps} />}
            </motion.div>
          </AnimatePresence>

          {/* ── Navigation bar — hidden on the final step (StepStart has its own CTAs) ── */}
          {!isLastStep && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.18 }}
              className="mt-8 flex items-center justify-between border-t border-border/40 pt-6"
            >
              {/* Back — only shown from step 2 onwards */}
              {currentStep > 1 ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={goBack}
                  className="gap-1.5"
                >
                  <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                  Back
                </Button>
              ) : (
                // Placeholder to keep "Continue" right-aligned on step 1
                <div />
              )}

              {/* Continue */}
              <Button
                onClick={goNext}
                disabled={!canAdvance}
                className="gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40"
              >
                Continue
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </motion.div>
          )}

          {/* ── Keyboard hint — only shown when Enter will actually work ── */}
          {!isLastStep && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: canAdvance ? 1 : 0 }}
              transition={{ duration: 0.3, delay: canAdvance ? 0.5 : 0 }}
              className="mt-4 text-center text-xs text-muted-foreground/60"
              aria-hidden="true"
            >
              Press{" "}
              <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">
                Enter
              </kbd>{" "}
              to continue
              {currentStep > 1 && (
                <>
                  {" · "}
                  <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">
                    Esc
                  </kbd>{" "}
                  to go back
                </>
              )}
            </motion.p>
          )}
        </div>
      </div>
    </>
  );
}
