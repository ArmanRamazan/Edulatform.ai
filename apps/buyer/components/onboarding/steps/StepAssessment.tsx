"use client";

import { Check, BrainCircuit } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { StepProps } from "@/components/onboarding/OnboardingWizard";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const SKILL_GROUPS = [
  {
    group: "Frontend",
    skills: ["React", "Next.js", "TypeScript", "CSS / Tailwind", "Vue"],
  },
  {
    group: "Backend",
    skills: ["Python", "Node.js", "Go", "Rust", "Java"],
  },
  {
    group: "Data & AI",
    skills: ["PostgreSQL", "Redis", "Kafka", "Vector DBs", "LLMs / RAG"],
  },
  {
    group: "Infrastructure",
    skills: ["Docker", "Kubernetes", "Terraform", "CI/CD", "AWS / GCP / Azure"],
  },
] as const;

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export function StepAssessment({ data, setData }: StepProps) {
  function toggleSkill(skill: string) {
    const next = data.skills.includes(skill)
      ? data.skills.filter((s) => s !== skill)
      : [...data.skills, skill];
    setData({ ...data, skills: next });
  }

  return (
    <div>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="mb-6 text-center"
      >
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
          <BrainCircuit className="h-6 w-6 text-primary" />
        </div>
        <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
          What do you work with?
        </h2>
        <p className="text-sm text-muted-foreground">
          Select all technologies your team uses — select at least one
        </p>
      </motion.div>

      {/* Skill groups */}
      <motion.div
        className="space-y-5"
        initial="hidden"
        animate="visible"
        variants={{
          visible: { transition: { staggerChildren: 0.1 } },
          hidden: {},
        }}
      >
        {SKILL_GROUPS.map(({ group, skills }) => (
          <motion.div
            key={group}
            variants={{ hidden: { opacity: 0, y: 8 }, visible: { opacity: 1, y: 0 } }}
          >
            <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              {group}
            </p>
            <div className="flex flex-wrap gap-2">
              {skills.map((skill) => {
                const isSelected = data.skills.includes(skill);
                return (
                  <motion.button
                    key={skill}
                    type="button"
                    onClick={() => toggleSkill(skill)}
                    whileTap={{ scale: 0.94 }}
                    className={cn(
                      "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium",
                      "outline-none transition-all duration-200",
                      "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                      isSelected
                        ? "border-primary bg-primary/15 text-primary shadow-[0_0_8px_rgba(124,92,252,0.25)]"
                        : "border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground",
                    )}
                  >
                    {isSelected && (
                      <Check className="h-3 w-3 shrink-0" strokeWidth={2.5} />
                    )}
                    {skill}
                  </motion.button>
                );
              })}
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* Selection count */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="mt-5 text-center text-xs text-muted-foreground"
      >
        {data.skills.length === 0 ? (
          "Select at least one skill to continue"
        ) : (
          <span>
            <span className="font-semibold text-primary">{data.skills.length}</span>
            {" "}skill{data.skills.length !== 1 ? "s" : ""} selected
          </span>
        )}
      </motion.p>
    </div>
  );
}
