import Link from "next/link";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  /** Lucide icon component to display */
  icon: LucideIcon;
  /** Short headline — e.g. "No recent activity" */
  title: string;
  /** Supporting sentence — one line max */
  description: string;
  /** Optional primary CTA that navigates to a page */
  action?: {
    label: string;
    href: string;
  };
  /** Extra className on the root container */
  className?: string;
}

/**
 * Reusable empty-state block for the Dark Knowledge theme.
 *
 * Renders: muted icon circle → title → description → optional CTA link.
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
    <div
      className={[
        "flex flex-col items-center justify-center gap-3 py-8 text-center",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {/* Icon bubble */}
      <div
        className="flex size-12 items-center justify-center rounded-full bg-secondary ring-1 ring-border/40"
        aria-hidden="true"
      >
        <Icon
          className="size-5 text-muted-foreground/50"
          strokeWidth={1.5}
          aria-hidden="true"
        />
      </div>

      {/* Copy */}
      <div className="max-w-[220px] space-y-1">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <p className="text-xs leading-relaxed text-muted-foreground/60">
          {description}
        </p>
      </div>

      {/* CTA */}
      {action && (
        <Link
          href={action.href}
          className="mt-1 rounded-lg bg-primary/10 px-4 py-1.5 text-xs font-semibold text-primary ring-1 ring-primary/20 transition-all hover:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {action.label}
        </Link>
      )}
    </div>
  );
}
