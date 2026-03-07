"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

interface EmptyStateAction {
  label: string;
  /** Navigate to a route — mutually exclusive with onClick */
  href?: string;
  /** Fire a callback instead of navigating */
  onClick?: () => void;
}

interface EmptyStateProps {
  /** Lucide icon component to display */
  icon: LucideIcon;
  /** Short headline — e.g. "No recent activity" */
  title: string;
  /** Supporting sentence — one line max */
  description: string;
  /** Optional primary CTA */
  action?: EmptyStateAction;
  /** Extra className on the root container */
  className?: string;
}

/**
 * Reusable empty-state block for the Dark Knowledge theme.
 *
 * Renders: muted icon circle → title → description → optional CTA.
 * Animates in with a subtle fade+scale on mount (framer-motion).
 * Intended for use inside Card bodies, page sections, and list placeholders.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97, y: 6 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className={[
        "flex flex-col items-center justify-center gap-3 py-8 text-center",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {/* Icon bubble */}
      <div
        className="flex size-12 items-center justify-center rounded-full bg-primary/8 ring-1 ring-primary/15"
        aria-hidden="true"
      >
        <Icon
          className="size-5 text-muted-foreground/60"
          strokeWidth={1.5}
          aria-hidden="true"
        />
      </div>

      {/* Copy */}
      <div className="max-w-[220px] space-y-1">
        <p className="text-sm font-medium text-foreground/80">{title}</p>
        <p className="text-xs leading-relaxed text-muted-foreground/60">
          {description}
        </p>
      </div>

      {/* CTA */}
      {action && (
        action.href ? (
          <Link
            href={action.href}
            className="mt-1 rounded-lg bg-primary/10 px-4 py-1.5 text-xs font-semibold text-primary ring-1 ring-primary/20 transition-all hover:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {action.label}
          </Link>
        ) : (
          <button
            type="button"
            onClick={action.onClick}
            className="mt-1 rounded-lg bg-primary/10 px-4 py-1.5 text-xs font-semibold text-primary ring-1 ring-primary/20 transition-all hover:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {action.label}
          </button>
        )
      )}
    </motion.div>
  );
}
