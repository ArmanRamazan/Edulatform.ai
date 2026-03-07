"use client";

import { useState } from "react";
import { Building2, Users } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { StepProps } from "@/components/onboarding/OnboardingWizard";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const ORG_SIZES = [
  { id: "1-10",    label: "1 – 10",    desc: "Small team" },
  { id: "11-50",   label: "11 – 50",   desc: "Growing startup" },
  { id: "51-200",  label: "51 – 200",  desc: "Mid-size company" },
  { id: "200+",    label: "200+",      desc: "Enterprise" },
] as const;

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export function StepOrganization({ data, setData }: StepProps) {
  // Validate on blur only — show error after first touch, not on every keystroke
  const [nameTouched, setNameTouched] = useState(false);
  const nameIsEmpty = nameTouched && data.orgName.trim().length === 0;

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
          <Building2 className="h-6 w-6 text-primary" />
        </div>
        <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
          Set up your organization
        </h2>
        <p className="text-sm text-muted-foreground">
          Tell us about your team so we can tailor the knowledge base
        </p>
      </motion.div>

      {/* Org name */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.08 }}
        className="mb-6"
      >
        <label
          htmlFor="org-name"
          className="mb-1.5 block text-sm font-medium text-foreground"
        >
          Organization name
          <span className="ml-1 text-primary" aria-hidden="true">*</span>
          <span className="sr-only">(required)</span>
        </label>
        <Input
          id="org-name"
          placeholder="Acme Corp"
          value={data.orgName}
          onChange={(e) => setData({ ...data, orgName: e.target.value })}
          onBlur={() => setNameTouched(true)}
          className={cn(
            "bg-card transition-colors duration-200",
            nameIsEmpty && "border-destructive ring-1 ring-destructive/50 focus-visible:ring-destructive",
          )}
          aria-invalid={nameIsEmpty}
          aria-describedby={nameIsEmpty ? "org-name-error" : undefined}
          autoFocus
          autoComplete="organization"
        />
        {/* Inline error — animated in, linked via aria-describedby */}
        <AnimatePresence>
          {nameIsEmpty && (
            <motion.p
              id="org-name-error"
              role="alert"
              initial={{ opacity: 0, y: -4, height: 0 }}
              animate={{ opacity: 1, y: 0, height: "auto" }}
              exit={{ opacity: 0, y: -4, height: 0 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className="mt-1.5 overflow-hidden text-xs text-destructive"
            >
              Organization name is required to continue
            </motion.p>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Org size */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.14 }}
      >
        <p className="mb-3 flex items-center gap-1.5 text-sm font-medium text-foreground">
          <Users className="h-4 w-4 text-muted-foreground" />
          Team size
          <span className="ml-0.5 text-xs text-muted-foreground">(optional)</span>
        </p>

        <motion.div
          className="grid grid-cols-2 gap-2 sm:grid-cols-4"
          initial="hidden"
          animate="visible"
          variants={{
            visible: { transition: { staggerChildren: 0.06 } },
            hidden: {},
          }}
        >
          {ORG_SIZES.map(({ id, label, desc }) => {
            const isSelected = data.orgSize === id;
            return (
              <motion.button
                key={id}
                type="button"
                aria-pressed={isSelected}
                onClick={() =>
                  setData({
                    ...data,
                    orgSize: isSelected ? null : id,
                  })
                }
                variants={{
                  hidden: { opacity: 0, y: 8 },
                  visible: { opacity: 1, y: 0 },
                }}
                whileHover={{ y: -1 }}
                whileTap={{ scale: 0.97 }}
                className={cn(
                  "rounded-xl border-2 px-3 py-3 text-left outline-none",
                  "transition-all duration-200",
                  "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  isSelected
                    ? "border-primary bg-primary/10 shadow-[0_0_16px_rgba(124,92,252,0.18)]"
                    : "border-border bg-card hover:border-primary/40",
                )}
              >
                <p className="text-sm font-semibold text-foreground">
                  {label}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">{desc}</p>
              </motion.button>
            );
          })}
        </motion.div>
      </motion.div>

    </div>
  );
}
