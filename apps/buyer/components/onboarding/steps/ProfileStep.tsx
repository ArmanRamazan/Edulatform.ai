"use client";

import { useEffect, useRef } from "react";
import {
  CheckCircle2,
  Code2,
  Crown,
  GraduationCap,
  Shield,
  UserCircle2,
} from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import type { StepProps } from "@/components/onboarding/OnboardingWizard";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const ROLE_OPTIONS = [
  {
    id: "junior",
    label: "Junior",
    desc: "Building fundamentals, first production systems",
    icon: GraduationCap,
    colorClass: "text-success",
    bgClass: "bg-success/10",
    borderSelected: "border-success",
    glowSelected: "shadow-[0_0_20px_rgba(52,211,153,0.18)]",
  },
  {
    id: "mid",
    label: "Mid",
    desc: "Shipping features solo, designing small systems",
    icon: Code2,
    colorClass: "text-info",
    bgClass: "bg-info/10",
    borderSelected: "border-info",
    glowSelected: "shadow-[0_0_20px_rgba(56,189,248,0.18)]",
  },
  {
    id: "senior",
    label: "Senior",
    desc: "Owning domains, mentoring, driving architecture",
    icon: Shield,
    colorClass: "text-warning",
    bgClass: "bg-warning/10",
    borderSelected: "border-warning",
    glowSelected: "shadow-[0_0_20px_rgba(251,191,36,0.18)]",
  },
  {
    id: "lead",
    label: "Lead",
    desc: "Setting technical direction, building culture",
    icon: Crown,
    colorClass: "text-primary",
    bgClass: "bg-primary/10",
    borderSelected: "border-primary",
    glowSelected: "shadow-[0_0_20px_rgba(124,92,252,0.22)]",
  },
] as const;

const STACK_OPTIONS = [
  {
    id: "python",
    label: "Python",
    symbol: "🐍",
    tags: ["AI / ML", "Backend", "Data"],
  },
  {
    id: "rust",
    label: "Rust",
    symbol: "🦀",
    tags: ["Systems", "Perf", "Safety"],
  },
  {
    id: "typescript",
    label: "TypeScript",
    symbol: "TS",
    tags: ["Web", "Frontend", "Full-stack"],
  },
  {
    id: "go",
    label: "Go",
    symbol: "Go",
    tags: ["Cloud", "DevOps", "Backend"],
  },
  {
    id: "java",
    label: "Java",
    symbol: "☕",
    tags: ["Enterprise", "JVM", "Backend"],
  },
] as const;

// ─────────────────────────────────────────────────────────────────────────────
// Animation helpers
// ─────────────────────────────────────────────────────────────────────────────

const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.07 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
};

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

/** True when `symbol` is a Latin abbreviation ("TS", "Go") rather than an emoji. */
function isTextSymbol(symbol: string): boolean {
  return /^[a-zA-Z]+$/.test(symbol);
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export function ProfileStep({ data, setData }: StepProps) {
  const { token } = useAuth();
  // Guard: only fire the PATCH once per completed profile selection
  const patchedRef = useRef(false);

  // Fire-and-forget PATCH /users/me when both role and stack are set
  useEffect(() => {
    if (!data.role || !data.stack || !token || patchedRef.current) return;
    patchedRef.current = true;
    fetch("/api/identity/users/me", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ role: data.role, primary_stack: data.stack }),
    }).catch(() => {
      // Non-blocking — ignore failures silently
    });
  }, [data.role, data.stack, token]);

  const bothSelected = data.role !== null && data.stack !== null;

  return (
    <div>
      {/* ── Header ── */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="mb-8 text-center"
      >
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
          <UserCircle2 className="h-6 w-6 text-primary" />
        </div>
        <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
          Your engineering profile
        </h2>
        <p className="text-sm text-muted-foreground">
          Personalize your knowledge missions and team insights
        </p>
      </motion.div>

      {/* ── Section A: Role ── */}
      <section aria-labelledby="profile-role-heading" className="mb-8">
        <motion.p
          id="profile-role-heading"
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.08 }}
          className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground"
        >
          What&apos;s your role?
        </motion.p>

        <motion.div
          className="grid grid-cols-2 gap-3 sm:grid-cols-4"
          initial="hidden"
          animate="visible"
          variants={staggerContainer}
        >
          {ROLE_OPTIONS.map(
            ({
              id,
              label,
              desc,
              icon: Icon,
              colorClass,
              bgClass,
              borderSelected,
              glowSelected,
            }) => {
              const isSelected = data.role === id;
              return (
                <motion.button
                  key={id}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => setData({ ...data, role: id })}
                  variants={fadeUp}
                  whileHover={{ y: -2, scale: 1.02 }}
                  whileTap={{ scale: 0.97 }}
                  className={cn(
                    "relative flex flex-col items-start rounded-xl border-2 p-4 text-left outline-none transition-all duration-200",
                    "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                    isSelected
                      ? cn("bg-card", borderSelected, glowSelected)
                      : "border-border bg-card hover:border-primary/40",
                  )}
                >
                  {/* Selected checkmark */}
                  {isSelected && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.5 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="absolute right-2.5 top-2.5"
                    >
                      <CheckCircle2 className={cn("h-4 w-4", colorClass)} />
                    </motion.div>
                  )}

                  {/* Icon badge */}
                  <div
                    className={cn(
                      "mb-3 flex h-9 w-9 items-center justify-center rounded-lg transition-colors duration-200",
                      isSelected
                        ? cn(bgClass, colorClass)
                        : "bg-muted text-muted-foreground",
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </div>

                  <p className="mb-0.5 text-sm font-semibold text-foreground">
                    {label}
                  </p>
                  <p className="text-[11px] leading-relaxed text-muted-foreground">
                    {desc}
                  </p>
                </motion.button>
              );
            },
          )}
        </motion.div>
      </section>

      {/* ── Section B: Tech Stack ── */}
      <section aria-labelledby="profile-stack-heading">
        <motion.p
          id="profile-stack-heading"
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.18 }}
          className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground"
        >
          Primary tech stack?
        </motion.p>

        <motion.div
          className="grid grid-cols-2 gap-3 sm:grid-cols-5"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: {
              transition: { staggerChildren: 0.07, delayChildren: 0.18 },
            },
          }}
        >
          {STACK_OPTIONS.map(({ id, label, symbol, tags }) => {
            const isSelected = data.stack === id;
            const isText = isTextSymbol(symbol);
            return (
              <motion.button
                key={id}
                type="button"
                aria-pressed={isSelected}
                onClick={() => setData({ ...data, stack: id })}
                variants={fadeUp}
                whileHover={{ y: -2, scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                className={cn(
                  "relative flex flex-col items-center rounded-xl border-2 p-4 text-center outline-none transition-all duration-200",
                  "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  isSelected
                    ? "border-primary bg-primary/5 shadow-[0_0_20px_rgba(124,92,252,0.22)]"
                    : "border-border bg-card hover:border-primary/40",
                )}
              >
                {/* Selected checkmark */}
                {isSelected && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="absolute right-2 top-2"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                  </motion.div>
                )}

                {/* Symbol badge */}
                <div
                  className={cn(
                    "mb-2.5 flex h-10 w-10 select-none items-center justify-center rounded-xl transition-colors duration-200",
                    isSelected ? "bg-primary/15" : "bg-muted",
                  )}
                >
                  <span
                    className={cn(
                      isText
                        ? cn(
                            "font-mono text-xs font-bold",
                            isSelected ? "text-primary" : "text-foreground",
                          )
                        : "text-xl",
                    )}
                  >
                    {symbol}
                  </span>
                </div>

                <p className="mb-1.5 text-xs font-semibold text-foreground">
                  {label}
                </p>

                {/* Tag pills */}
                <div className="flex flex-wrap justify-center gap-1">
                  {tags.map((tag) => (
                    <span
                      key={tag}
                      className={cn(
                        "rounded-full px-1.5 py-0.5 text-[9px] font-medium transition-colors duration-200",
                        isSelected
                          ? "bg-primary/20 text-primary/80"
                          : "bg-muted text-muted-foreground",
                      )}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </motion.button>
            );
          })}
        </motion.div>
      </section>

      {/* ── Completion hint ── */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.45 }}
        className="mt-5 text-center text-xs text-muted-foreground"
      >
        {bothSelected ? (
          <motion.span
            key="complete"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-success"
          >
            Profile complete — ready to continue
          </motion.span>
        ) : !data.role ? (
          "Select your role to continue"
        ) : (
          "Select your primary stack to continue"
        )}
      </motion.p>
    </div>
  );
}
