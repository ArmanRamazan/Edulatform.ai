"use client";

import {
  ArrowRight,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  Layers,
  Trophy,
} from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { StepProps } from "@/components/onboarding/OnboardingWizard";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const NEXT_STEPS = [
  {
    href: "/graph",
    icon: BrainCircuit,
    label: "Explore the knowledge graph",
    desc: "Navigate your team's connected concepts visually",
    iconClass: "text-primary",
    bgClass: "bg-primary/10",
  },
  {
    href: "/missions",
    icon: BookOpen,
    label: "Start your first mission",
    desc: "AI-guided learning path based on your skills",
    iconClass: "text-info",
    bgClass: "bg-info/10",
  },
  {
    href: "/flashcards",
    icon: Layers,
    label: "Review with flashcards",
    desc: "Spaced repetition powered by FSRS algorithm",
    iconClass: "text-success",
    bgClass: "bg-success/10",
  },
  {
    href: "/badges",
    icon: Trophy,
    label: "Track XP and badges",
    desc: "See your team progress, streaks, and achievements",
    iconClass: "text-warning",
    bgClass: "bg-warning/10",
  },
] as const;

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export function StepStart({ data }: StepProps) {
  const orgName = data.orgName.trim() || "your organization";

  return (
    <div className="text-center">
      {/* Success icon */}
      <motion.div
        initial={{ opacity: 0, scale: 0.4 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 220, damping: 14 }}
        className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-success/15 ring-1 ring-success/30"
      >
        <CheckCircle2 className="h-8 w-8 text-success" />
      </motion.div>

      {/* Text */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mb-8"
      >
        <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
          {orgName} is ready to go!
        </h2>
        <p className="text-sm text-muted-foreground">
          Your knowledge base is set up. Here&apos;s where to start:
        </p>
      </motion.div>

      {/* Next-step links */}
      <motion.div
        className="mx-auto mb-8 grid max-w-lg gap-2.5"
        initial="hidden"
        animate="visible"
        variants={{
          visible: {
            transition: { staggerChildren: 0.09, delayChildren: 0.3 },
          },
          hidden: {},
        }}
      >
        {NEXT_STEPS.map(({ href, icon: Icon, label, desc, iconClass, bgClass }) => (
          <motion.div
            key={href}
            variants={{ hidden: { opacity: 0, x: -12 }, visible: { opacity: 1, x: 0 } }}
          >
            <Link
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-xl border border-border bg-card p-4 text-left",
                "transition-all hover:border-primary/40 hover:bg-muted/20",
              )}
            >
              <div className={cn("shrink-0 rounded-lg p-2", bgClass)}>
                <Icon className={cn("h-4 w-4", iconClass)} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-foreground">{label}</p>
                <p className="text-xs text-muted-foreground">{desc}</p>
              </div>
              <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
            </Link>
          </motion.div>
        ))}
      </motion.div>

      {/* Primary CTA */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.75 }}
      >
        <Button
          asChild
          size="lg"
          className={cn(
            "gap-2 bg-primary px-8",
            "shadow-[0_0_20px_rgba(124,92,252,0.3)]",
            "hover:bg-primary/90 hover:shadow-[0_0_28px_rgba(124,92,252,0.45)]",
          )}
        >
          <Link href="/dashboard">
            Go to dashboard
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </motion.div>
    </div>
  );
}
