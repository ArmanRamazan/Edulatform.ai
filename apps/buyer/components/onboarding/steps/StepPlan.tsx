"use client";

import { CheckCircle2, Flame, Rocket, Sprout, Users } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { StepProps } from "@/components/onboarding/OnboardingWizard";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const LEARNING_GOALS = [
  {
    id: "onboard",
    icon: Rocket,
    label: "Onboard fast",
    desc: "Get new engineers productive within their first two weeks",
    iconClass: "text-primary",
    bgClass: "bg-primary/10",
  },
  {
    id: "deepen",
    icon: Sprout,
    label: "Deepen skills",
    desc: "Strengthen existing knowledge and fill individual gaps",
    iconClass: "text-success",
    bgClass: "bg-success/10",
  },
  {
    id: "standards",
    icon: Flame,
    label: "Build standards",
    desc: "Define and propagate engineering best practices across the team",
    iconClass: "text-warning",
    bgClass: "bg-warning/10",
  },
  {
    id: "team",
    icon: Users,
    label: "Grow the team",
    desc: "Scale engineering capability while preserving code quality",
    iconClass: "text-info",
    bgClass: "bg-info/10",
  },
] as const;

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export function StepPlan({ data, setData }: StepProps) {
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
          <Flame className="h-6 w-6 text-primary" />
        </div>
        <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
          What&apos;s your primary goal?
        </h2>
        <p className="text-sm text-muted-foreground">
          We&apos;ll build a learning plan and suggest missions around this focus
        </p>
      </motion.div>

      {/* Goal cards */}
      <motion.div
        className="grid gap-3 sm:grid-cols-2"
        initial="hidden"
        animate="visible"
        variants={{
          visible: { transition: { staggerChildren: 0.08 } },
          hidden: {},
        }}
      >
        {LEARNING_GOALS.map(({ id, icon: Icon, label, desc, iconClass, bgClass }) => {
          const isSelected = data.goal === id;
          return (
            <motion.button
              key={id}
              type="button"
              aria-pressed={isSelected}
              onClick={() => setData({ ...data, goal: id })}
              variants={{
                hidden: { opacity: 0, scale: 0.96 },
                visible: { opacity: 1, scale: 1 },
              }}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.97 }}
              className={cn(
                "relative rounded-xl border-2 p-5 text-left outline-none transition-all duration-200",
                "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                isSelected
                  ? "border-primary bg-primary/10 shadow-[0_0_20px_rgba(124,92,252,0.2)]"
                  : "border-border bg-card hover:border-primary/40",
              )}
            >
              {isSelected && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.5 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="absolute right-3 top-3"
                >
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                </motion.div>
              )}
              <div
                className={cn(
                  "mb-3 inline-flex rounded-lg p-2 transition-colors",
                  isSelected ? cn(bgClass, iconClass) : "bg-muted text-muted-foreground",
                )}
              >
                <Icon className="h-5 w-5" />
              </div>
              <p className="mb-1 font-semibold text-foreground">{label}</p>
              <p className="text-xs leading-relaxed text-muted-foreground">{desc}</p>
            </motion.button>
          );
        })}
      </motion.div>
    </div>
  );
}
