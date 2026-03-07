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
// Utility — deterministic accent color from org name
// Gives each org visual identity without dynamic Tailwind class generation.
// ─────────────────────────────────────────────────────────────────────────────

function getOrgAccentColor(name: string): string {
  // Dark Knowledge palette — all feel at home on #14141f
  const palette = [
    "#7c5cfc", // violet  (primary)
    "#38bdf8", // sky     (info)
    "#34d399", // emerald (success)
    "#fbbf24", // amber   (warning)
    "#a78bfa", // lavender
    "#f472b6", // pink
  ];
  let h = 0;
  for (let i = 0; i < name.length; i++) {
    h = ((h << 5) - h + name.charCodeAt(i)) | 0;
  }
  return palette[Math.abs(h) % palette.length];
}

// ─────────────────────────────────────────────────────────────────────────────
// OrgCardSkeleton — placeholder while loading (stagger-aware)
// ─────────────────────────────────────────────────────────────────────────────

function OrgCardSkeleton({ index }: { index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: index * 0.07, ease: "easeOut" }}
      className="flex flex-col items-center gap-4 rounded-xl border border-border bg-card p-6"
    >
      <Skeleton className="h-14 w-14 rounded-xl" />
      <div className="flex w-full flex-col items-center gap-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <Skeleton className="h-5 w-20 rounded-full" />
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// OrgCardItem — single selectable org card with member count
// ─────────────────────────────────────────────────────────────────────────────

interface OrgCardItemProps {
  org: Organization;
  /** Position in the grid — used for tabIndex: first card is keyboard-reachable by default */
  index: number;
  selected: boolean;
  /** Null when nothing is selected yet — first card gets tabIndex=0 in that case */
  selectedOrgId: string | null;
  autoSelecting: boolean;
  onSelect: (org: Organization) => void;
}

function OrgCardItem({ org, index, selected, selectedOrgId, autoSelecting, onSelect }: OrgCardItemProps) {
  const { token } = useAuth();
  const membersQuery = useOrgMembers(token, org.id);
  const memberCount = membersQuery.data?.length ?? null;
  const firstLetter = org.name.charAt(0).toUpperCase();
  const accentColor = getOrgAccentColor(org.name);

  return (
    <motion.button
      type="button"
      role="radio"
      aria-checked={selected}
      // ARIA radiogroup keyboard contract: only one button in the tab order at a time.
      // Selected card = 0, unselected = -1. If nothing selected, first card = 0.
      tabIndex={selected || (!selectedOrgId && index === 0) ? 0 : -1}
      aria-disabled={autoSelecting && !selected}
      onClick={() => !autoSelecting && onSelect(org)}
      whileHover={!autoSelecting ? { y: -2 } : {}}
      whileTap={!autoSelecting ? { scale: 0.98 } : {}}
      className={cn(
        // Layout & shape — overflow-hidden required so the progress bar clips to rounded-xl
        "relative flex w-full flex-col items-center gap-4 overflow-hidden rounded-xl border p-6 text-center outline-none",
        // Transition — exclude transform so Framer Motion owns it cleanly
        "transition-[border-color,background-color,box-shadow] duration-200",
        // Focus ring
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        // Selected: org-colored border + layered ambient glow (3-layer for depth)
        // Background is set via inline `style` below so it uses the org's accentColor.
        selected
          ? "border-primary shadow-[0_0_0_1px_rgba(124,92,252,0.5),0_0_28px_rgba(124,92,252,0.22),0_0_64px_rgba(124,92,252,0.08)]"
          : "border-white/[0.06] bg-card hover:border-primary/40 hover:bg-primary/[0.04]",
        autoSelecting && !selected && "cursor-default opacity-40",
      )}
      // Personalize the selected card tint to the org's accent color
      style={selected ? { backgroundColor: `${accentColor}12` } : undefined}
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

      {/* Logo avatar — letter color derived deterministically from org name */}
      <Avatar className="h-14 w-14 rounded-xl">
        {org.logo_url ? (
          <AvatarImage src={org.logo_url} alt={org.name} className="rounded-xl object-cover" />
        ) : null}
        <AvatarFallback
          className="rounded-xl text-xl font-semibold transition-[background-color,box-shadow] duration-200"
          style={{
            backgroundColor: `${accentColor}18`,
            color: accentColor,
            // Selected: brighten the avatar chip with a soft inner glow
            boxShadow: selected ? `0 0 0 1.5px ${accentColor}40, inset 0 0 12px ${accentColor}18` : "none",
          }}
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
        className="gap-1 text-xs transition-[border-color,color,background-color] duration-200"
        style={
          selected
            ? { borderColor: `${accentColor}50`, color: accentColor, backgroundColor: `${accentColor}0d` }
            : {}
        }
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

      {/* Auto-select progress bar — gradient + subtle glow */}
      {selected && autoSelecting && (
        <motion.div
          className="absolute bottom-0 left-0 h-[3px] rounded-b-xl"
          style={{
            background: "linear-gradient(90deg, #7c5cfc 0%, #a78bfa 60%, #c4b5fd 100%)",
            boxShadow: "0 0 8px rgba(124,92,252,0.6)",
          }}
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

  // Auto-focus the first card once orgs load — keyboard-first: no mouse needed.
  // Only fires when nothing is selected yet (auto-select will set focus itself via
  // the radiogroup's tabIndex, so we skip this path when autoSelecting).
  useEffect(() => {
    if (!orgs || orgs.length === 0 || selectedOrgId) return;
    const id = requestAnimationFrame(() => {
      const firstCard = gridRef.current?.querySelector<HTMLButtonElement>('[role="radio"]');
      firstCard?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgs?.length]);

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
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }}>
        <div className="mb-8 text-center">
          {/* Icon chip placeholder — matches the h-12 w-12 chip in the loaded state */}
          <Skeleton className="mx-auto mb-4 h-12 w-12 rounded-xl" />
          <Skeleton className="mx-auto mb-2 h-7 w-56" />
          <Skeleton className="mx-auto h-4 w-64" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <OrgCardSkeleton key={i} index={i} />
          ))}
        </div>
      </motion.div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────

  if (isError) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="flex flex-col items-center gap-4 py-12 text-center"
      >
        <div
          className="flex h-14 w-14 items-center justify-center rounded-xl border border-destructive/25 bg-destructive/10"
          style={{ boxShadow: "0 0 20px rgba(248,113,113,0.15), 0 0 40px rgba(248,113,113,0.06)" }}
        >
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
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="flex flex-col items-center gap-5 py-12 text-center"
      >
        {/* Icon — muted/neutral: this state isn't an error, just an empty slate */}
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted/60 ring-1 ring-border">
          <Building2 className="h-6 w-6 text-muted-foreground" />
        </div>
        <div>
          <p className="font-semibold text-foreground">No organizations yet</p>
          <p className="mt-1 max-w-[22rem] text-sm text-muted-foreground">
            Ask your admin for an invite, then check again.
          </p>
        </div>
        {/* "Check again" — lets user retry without reloading the page */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void refetch()}
          className="gap-1.5 text-muted-foreground hover:text-foreground"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Check again
        </Button>
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
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="mb-8 text-center"
      >
        {/* Icon chip — 48px, matches other wizard step headers */}
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
          <Building2 className="h-6 w-6 text-primary" />
        </div>
        <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
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
        {orgs.map((org, orgIdx) => (
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
              index={orgIdx}
              selected={selectedOrgId === org.id}
              selectedOrgId={selectedOrgId}
              autoSelecting={autoSelecting}
              onSelect={handleSelect}
            />
          </motion.div>
        ))}
      </motion.div>

      {/* Keyboard navigation hint — mirrors the Enter/Esc hint shown on other steps */}
      {orgs.length > 1 && !autoSelecting && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, delay: 0.6 }}
          className="mt-4 text-center text-xs text-muted-foreground/50"
          aria-hidden="true"
        >
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">
            ↑
          </kbd>{" "}
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">
            ↓
          </kbd>{" "}
          arrow keys to navigate
        </motion.p>
      )}
    </div>
  );
}
