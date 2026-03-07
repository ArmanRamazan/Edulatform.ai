"use client";

import { CheckCircle2, Layers } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { StepProps } from "@/components/onboarding/OnboardingWizard";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const EXPERIENCE_LEVELS = [
  {
    id: "junior",
    label: "Junior",
    yearsRange: "0 – 2 yrs",
    desc: "Learning the fundamentals, building first production systems",
    colorClass: "text-success",
    bgClass: "bg-success/10",
    borderSelected: "border-success",
    shadowSelected: "shadow-[0_0_16px_rgba(52,211,153,0.18)]",
  },
  {
    id: "mid",
    label: "Mid-level",
    yearsRange: "2 – 5 yrs",
    desc: "Shipping features independently, designing small systems",
    colorClass: "text-info",
    bgClass: "bg-info/10",
    borderSelected: "border-info",
    shadowSelected: "shadow-[0_0_16px_rgba(56,189,248,0.18)]",
  },
  {
    id: "senior",
    label: "Senior",
    yearsRange: "5 – 10 yrs",
    desc: "Owning domains, mentoring engineers, driving architecture",
    colorClass: "text-warning",
    bgClass: "bg-warning/10",
    borderSelected: "border-warning",
    shadowSelected: "shadow-[0_0_16px_rgba(251,191,36,0.18)]",
  },
  {
    id: "lead",
    label: "Tech Lead / Staff",
    yearsRange: "10+ yrs",
    desc: "Setting technical direction, building engineering culture",
    colorClass: "text-primary",
    bgClass: "bg-primary/10",
    borderSelected: "border-primary",
    shadowSelected: "shadow-[0_0_16px_rgba(124,92,252,0.2)]",
  },
] as const;

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export function StepExperience({ data, setData }: StepProps) {
  return (
    <div>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="mb-8 text-center"
      >
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
          <Layers className="h-6 w-6 text-primary" />
        </div>
        <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
          Your engineering experience
        </h2>
        <p className="text-sm text-muted-foreground">
          We&apos;ll calibrate mission difficulty and learning pace to your level
        </p>
      </motion.div>

      {/* Level cards */}
      <motion.div
        className="grid gap-3 sm:grid-cols-2"
        initial="hidden"
        animate="visible"
        variants={{
          visible: { transition: { staggerChildren: 0.08 } },
          hidden: {},
        }}
      >
        {EXPERIENCE_LEVELS.map(
          ({
            id,
            label,
            yearsRange,
            desc,
            colorClass,
            bgClass,
            borderSelected,
            shadowSelected,
          }) => {
            const isSelected = data.experience === id;
            return (
              <motion.button
                key={id}
                type="button"
                aria-pressed={isSelected}
                onClick={() => setData({ ...data, experience: id })}
                variants={{
                  hidden: { opacity: 0, y: 12 },
                  visible: { opacity: 1, y: 0 },
                }}
                whileHover={{ y: -2 }}
                whileTap={{ scale: 0.97 }}
                className={cn(
                  "relative rounded-xl border-2 p-5 text-left outline-none transition-all duration-200",
                  "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  isSelected
                    ? cn("bg-card", borderSelected, shadowSelected)
                    : "border-border bg-card hover:border-primary/40",
                )}
              >
                {isSelected && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="absolute right-3 top-3"
                  >
                    <CheckCircle2
                      className={cn("h-4 w-4", colorClass)}
                    />
                  </motion.div>
                )}
                <div
                  className={cn(
                    "mb-3 inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold transition-colors",
                    isSelected
                      ? cn(bgClass, colorClass)
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {yearsRange}
                </div>
                <p className="mb-1 font-semibold text-foreground">{label}</p>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  {desc}
                </p>
              </motion.button>
            );
          },
        )}
      </motion.div>
    </div>
  );
}
