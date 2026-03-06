"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, Building2, CheckCircle2, RefreshCw, Users } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useMyOrganizations, useOrgMembers } from "@/hooks/use-organizations";
import { useActiveOrg } from "@/hooks/use-active-org";
import { type Organization } from "@/lib/api";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────────────────────────────────────
// OrgCardSkeleton — placeholder while loading
// ─────────────────────────────────────────────────────────────────────────────

function OrgCardSkeleton() {
  return (
    <div className="flex flex-col items-center gap-4 rounded-xl border border-border bg-card p-6">
      <Skeleton className="h-14 w-14 rounded-xl" />
      <div className="flex w-full flex-col items-center gap-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <Skeleton className="h-5 w-20 rounded-full" />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// OrgCardItem — single selectable org card with member count
// ─────────────────────────────────────────────────────────────────────────────

interface OrgCardItemProps {
  org: Organization;
  selected: boolean;
  autoSelecting: boolean;
  onSelect: (org: Organization) => void;
}

function OrgCardItem({ org, selected, autoSelecting, onSelect }: OrgCardItemProps) {
  const { token } = useAuth();
  const membersQuery = useOrgMembers(token, org.id);
  const memberCount = membersQuery.data?.length ?? null;
  const firstLetter = org.name.charAt(0).toUpperCase();

  return (
    <motion.button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={() => !autoSelecting && onSelect(org)}
      whileHover={!autoSelecting ? { y: -2 } : {}}
      whileTap={!autoSelecting ? { scale: 0.98 } : {}}
      className={cn(
        // Layout & shape
        "relative flex w-full flex-col items-center gap-4 rounded-xl border p-6 text-center outline-none",
        // Transition — exclude transform so Framer Motion owns it cleanly
        "transition-[border-color,background-color,box-shadow] duration-200",
        // Focus ring
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        // Selected: violet border + inner ring + ambient glow
        selected
          ? "border-primary bg-primary/10 shadow-[0_0_0_1px_rgba(124,92,252,0.45),0_0_28px_rgba(124,92,252,0.18)]"
          : "border-border bg-card hover:border-primary/50 hover:bg-primary/[0.04]",
        autoSelecting && !selected && "cursor-default opacity-40",
      )}
    >
      {/* Selected checkmark */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.5 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="absolute right-3 top-3"
          >
            <CheckCircle2 className="h-5 w-5 text-primary" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Logo avatar */}
      <Avatar className="h-14 w-14 rounded-xl">
        {org.logo_url ? (
          <AvatarImage src={org.logo_url} alt={org.name} className="rounded-xl object-cover" />
        ) : null}
        <AvatarFallback
          className={cn(
            // font-semibold (600) — never font-bold (700) per design system
            "rounded-xl text-xl font-semibold transition-colors duration-200",
            selected ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground",
          )}
        >
          {firstLetter}
        </AvatarFallback>
      </Avatar>

      {/* Name + slug */}
      <div className="w-full min-w-0">
        <p className="truncate text-sm font-semibold leading-snug text-foreground">{org.name}</p>
        <p className="mt-0.5 truncate text-xs text-muted-foreground">{org.slug}</p>
      </div>

      {/* Member count badge — number uses font-mono per design system */}
      <Badge
        variant="outline"
        className={cn(
          "gap-1 text-xs transition-colors duration-200",
          selected ? "border-primary/40 text-primary" : "text-muted-foreground",
        )}
      >
        <Users className="h-3 w-3" />
        {membersQuery.isLoading ? (
          <span className="animate-pulse">···</span>
        ) : (
          <>
            <span className="font-mono tabular-nums">{memberCount ?? 0}</span>
            <span>member{memberCount !== 1 ? "s" : ""}</span>
          </>
        )}
      </Badge>

      {/* Auto-select progress bar */}
      {selected && autoSelecting && (
        <motion.div
          className="absolute bottom-0 left-0 h-[3px] rounded-b-xl bg-primary"
          initial={{ width: "0%" }}
          animate={{ width: "100%" }}
          transition={{ duration: 1, ease: "linear" }}
        />
      )}
    </motion.button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// OrgStep — Step 1 of onboarding: pick active organization
// ─────────────────────────────────────────────────────────────────────────────

export interface OrgStepProps {
  onNext: () => void;
}

export function OrgStep({ onNext }: OrgStepProps) {
  const { token } = useAuth();
  const { data: orgs, isLoading, isError, refetch } = useMyOrganizations(token);
  const { setActiveOrg } = useActiveOrg();
  const gridRef = useRef<HTMLDivElement>(null);

  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const [autoSelecting, setAutoSelecting] = useState(false);

  const handleSelect = useCallback(
    (org: Organization) => {
      setSelectedOrgId(org.id);
      setActiveOrg(org);
      // Brief pause so the selection animation renders before advancing
      setTimeout(() => onNext(), 150);
    },
    [setActiveOrg, onNext],
  );

  // Auto-select the only org with a 1s animated delay
  useEffect(() => {
    if (!orgs || orgs.length !== 1) return;

    setSelectedOrgId(orgs[0].id);
    setAutoSelecting(true);

    const timer = setTimeout(() => {
      handleSelect(orgs[0]);
    }, 1000);

    return () => clearTimeout(timer);
  }, [orgs, handleSelect]);

  // Arrow-key navigation within the radiogroup (ARIA radiogroup keyboard pattern)
  function handleGridKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    if (!["ArrowDown", "ArrowRight", "ArrowUp", "ArrowLeft"].includes(e.key)) return;
    e.preventDefault();

    const buttons = Array.from(
      gridRef.current?.querySelectorAll<HTMLButtonElement>('[role="radio"]') ?? [],
    );
    const idx = buttons.indexOf(document.activeElement as HTMLButtonElement);
    if (idx === -1) return;

    const dir = e.key === "ArrowDown" || e.key === "ArrowRight" ? 1 : -1;
    const next = buttons[(idx + dir + buttons.length) % buttons.length];
    next?.focus();
  }

  // ── Loading ──────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div>
        <div className="mb-6 text-center">
          <Skeleton className="mx-auto mb-3 h-7 w-56" />
          <Skeleton className="mx-auto h-4 w-64" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <OrgCardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────

  if (isError) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center gap-4 py-12 text-center"
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-border bg-destructive/10">
          <AlertCircle className="h-7 w-7 text-destructive" />
        </div>
        <div>
          <p className="font-semibold text-foreground">Failed to load organizations</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Check your connection and try again.
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void refetch()}
          className="gap-1.5 text-muted-foreground hover:text-foreground"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Try again
        </Button>
      </motion.div>
    );
  }

  // ── Empty state ──────────────────────────────────────────────────────────

  if (!orgs || orgs.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center gap-4 py-12 text-center"
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-border bg-card">
          <Building2 className="h-7 w-7 text-muted-foreground" />
        </div>
        <div>
          <p className="font-semibold text-foreground">No organizations found</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Ask your admin for an invite to get started.
          </p>
        </div>
      </motion.div>
    );
  }

  // ── Main grid ────────────────────────────────────────────────────────────

  return (
    <div>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 text-center"
      >
        <h2 className="mb-2 text-2xl font-semibold tracking-[-0.01em] text-foreground">
          Choose your organization
        </h2>
        <p className="text-sm text-muted-foreground">Select the workspace you want to join</p>
      </motion.div>

      {/* Auto-select banner */}
      <AnimatePresence>
        {autoSelecting && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-4 overflow-hidden"
          >
            <div className="flex items-center gap-2.5 rounded-lg border border-primary/40 bg-primary/10 px-4 py-2.5 text-sm text-primary">
              {/* Spinning ring */}
              <motion.div
                className="h-4 w-4 shrink-0 rounded-full border-2 border-primary/30 border-t-primary"
                animate={{ rotate: 360 }}
                transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
              />
              Auto-selecting your organization&hellip;
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Org grid — 2 cols on sm+, 1 col on mobile */}
      <motion.div
        ref={gridRef}
        role="radiogroup"
        aria-label="Select organization"
        className="grid gap-4 sm:grid-cols-2"
        onKeyDown={handleGridKeyDown}
        initial="hidden"
        animate="visible"
        variants={{
          visible: { transition: { staggerChildren: 0.08 } },
          hidden: {},
        }}
      >
        {orgs.map((org) => (
          <motion.div
            key={org.id}
            variants={{
              hidden: { opacity: 0, y: 12 },
              visible: { opacity: 1, y: 0 },
            }}
            transition={{ duration: 0.3 }}
          >
            <OrgCardItem
              org={org}
              selected={selectedOrgId === org.id}
              autoSelecting={autoSelecting}
              onSelect={handleSelect}
            />
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}
