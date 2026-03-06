"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, Building2, CheckCircle2, RotateCcw, Users } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useMyOrganizations, useOrgMembers } from "@/hooks/use-organizations";
import { useActiveOrg } from "@/hooks/use-active-org";
import { type Organization } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

/** Russian pluralisation for "участник" */
function memberLabel(n: number): string {
  if (n % 100 >= 11 && n % 100 <= 14) return `${n} участников`;
  const mod = n % 10;
  if (mod === 1) return `${n} участник`;
  if (mod >= 2 && mod <= 4) return `${n} участника`;
  return `${n} участников`;
}

// ─────────────────────────────────────────────────────────────────────────────
// OrgCard
// ─────────────────────────────────────────────────────────────────────────────

interface OrgCardProps {
  org: Organization;
  selected: boolean;
  index: number;
  onSelect: () => void;
}

function OrgCard({ org, selected, index, onSelect }: OrgCardProps) {
  const { token } = useAuth();
  const membersQuery = useOrgMembers(token, org.id);
  const memberCount = membersQuery.data?.length ?? 0;
  const initial = org.name.charAt(0).toUpperCase();

  return (
    <motion.button
      type="button"
      role="option"
      aria-selected={selected}
      aria-label={`Выбрать организацию ${org.name}`}
      onClick={onSelect}
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: index * 0.08, ease: "easeOut" }}
      whileHover={{ y: -3, transition: { duration: 0.15 } }}
      whileTap={{ scale: 0.97 }}
      className={cn(
        "group relative flex flex-col items-center gap-4 rounded-2xl border-2 p-6 text-center outline-none",
        "transition-all duration-200",
        "focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        selected
          ? "border-primary bg-primary/10 shadow-[0_0_32px_rgba(124,92,252,0.22)]"
          : "border-border bg-card hover:border-primary/50 hover:shadow-[0_0_20px_rgba(124,92,252,0.10)]",
      )}
    >
      {/* Selected checkmark badge */}
      <AnimatePresence>
        {selected && (
          <motion.div
            key="check"
            initial={{ opacity: 0, scale: 0.4 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.4 }}
            transition={{ duration: 0.18, type: "spring", stiffness: 300, damping: 20 }}
            className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-primary"
          >
            <CheckCircle2 className="h-3.5 w-3.5 text-white" strokeWidth={2.5} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Logo / Letter avatar */}
      <motion.div
        animate={
          selected
            ? { boxShadow: "0 4px 16px rgba(124,92,252,0.35)" }
            : { boxShadow: "0 0 0px rgba(124,92,252,0)" }
        }
        transition={{ duration: 0.2 }}
        className={cn(
          "flex h-16 w-16 shrink-0 items-center justify-center rounded-xl text-2xl font-bold transition-colors duration-200",
          selected
            ? "bg-primary text-white"
            : "bg-primary/10 text-primary group-hover:bg-primary/20",
        )}
      >
        {org.logo_url ? (
          <Image
            src={org.logo_url}
            alt={`${org.name} логотип`}
            width={40}
            height={40}
            className="h-10 w-10 rounded-lg object-cover"
          />
        ) : (
          <span>{initial}</span>
        )}
      </motion.div>

      {/* Name + slug */}
      <div className="flex flex-col gap-0.5">
        <h3 className="text-base font-semibold text-foreground">{org.name}</h3>
        <span className="text-xs text-muted-foreground">{org.slug}</span>
      </div>

      {/* Member count */}
      <div className="flex items-center gap-1.5">
        <Users className="h-3.5 w-3.5 text-muted-foreground" />
        {membersQuery.isLoading ? (
          <Skeleton className="h-3 w-16" />
        ) : (
          <span className="text-xs text-muted-foreground">{memberLabel(memberCount)}</span>
        )}
      </div>
    </motion.button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Skeleton cards — shape matches OrgCard exactly
// ─────────────────────────────────────────────────────────────────────────────

function OrgCardSkeleton({ delay = 0 }: { delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, delay }}
      className="flex flex-col items-center gap-4 rounded-2xl border border-border bg-card p-6"
    >
      {/* Avatar */}
      <Skeleton className="h-16 w-16 rounded-xl" />
      {/* Name + slug */}
      <div className="flex w-full flex-col items-center gap-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-3 w-20" />
      </div>
      {/* Member count */}
      <Skeleton className="h-3 w-24" />
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Auto-select banner (shown when exactly 1 org, 1-second countdown)
// ─────────────────────────────────────────────────────────────────────────────

function AutoSelectBanner({ orgName }: { orgName: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.2 }}
      className="flex items-center gap-2.5 rounded-xl border border-primary/30 bg-primary/10 px-4 py-2.5 text-sm text-primary"
      role="status"
      aria-live="polite"
    >
      {/* Spinning indicator */}
      <motion.span
        className="block h-4 w-4 rounded-full border-2 border-primary border-t-transparent"
        animate={{ rotate: 360 }}
        transition={{ duration: 0.7, repeat: Infinity, ease: "linear" }}
        aria-hidden="true"
      />
      Автовыбор: <strong>{orgName}</strong>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────

export default function OrgSelectPage() {
  const router = useRouter();
  const { token } = useAuth();
  const { data: orgs, isLoading, isError, refetch } = useMyOrganizations(token);
  const { setActiveOrg } = useActiveOrg();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [autoSelecting, setAutoSelecting] = useState(false);
  const autoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Select handler (stable ref via useCallback) ──────────────────────────
  const handleSelect = useCallback(
    (org: Organization) => {
      if (autoTimerRef.current) clearTimeout(autoTimerRef.current);
      setAutoSelecting(false);
      setActiveOrg(org);
      router.replace("/dashboard");
    },
    [setActiveOrg, router],
  );

  // ── Auto-select when exactly 1 org (1-second delay) ──────────────────────
  useEffect(() => {
    if (!orgs || orgs.length !== 1) return;

    const org = orgs[0];
    setSelectedId(org.id);
    setAutoSelecting(true);

    autoTimerRef.current = setTimeout(() => {
      handleSelect(org);
    }, 1000);

    return () => {
      if (autoTimerRef.current) clearTimeout(autoTimerRef.current);
    };
  }, [orgs, handleSelect]);

  // ── Keyboard navigation ───────────────────────────────────────────────────
  useEffect(() => {
    if (!orgs || orgs.length === 0) return;

    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedId((prev) => {
          const idx = prev ? orgs.findIndex((o) => o.id === prev) : -1;
          return orgs[(idx + 1) % orgs.length].id;
        });
      }
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedId((prev) => {
          const idx = prev ? orgs.findIndex((o) => o.id === prev) : 0;
          return orgs[(idx - 1 + orgs.length) % orgs.length].id;
        });
      }
      if (e.key === "Enter") {
        setSelectedId((prev) => {
          if (!prev) return prev;
          const org = orgs.find((o) => o.id === prev);
          if (org) handleSelect(org);
          return prev;
        });
      }
    };

    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [orgs, handleSelect]);

  // ── Loading ───────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-8 px-4">
        <div className="flex flex-col items-center gap-2 text-center">
          <Skeleton className="h-7 w-56" />
          <Skeleton className="h-4 w-44" />
        </div>
        <div className="grid w-full max-w-lg grid-cols-1 gap-4 sm:grid-cols-2">
          {[0, 1, 2].map((i) => (
            <OrgCardSkeleton key={i} delay={i * 0.06} />
          ))}
        </div>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center"
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
          <AlertCircle className="h-6 w-6 text-destructive" />
        </div>
        <div>
          <p className="font-semibold text-foreground">Не удалось загрузить организации</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Проверьте соединение и попробуйте снова
          </p>
        </div>
        <Button variant="outline" onClick={() => void refetch()} className="gap-2">
          <RotateCcw className="h-4 w-4" />
          Повторить
        </Button>
      </motion.div>
    );
  }

  // ── Empty ─────────────────────────────────────────────────────────────────
  if (!orgs || orgs.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center"
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <Building2 className="h-6 w-6 text-muted-foreground" />
        </div>
        <div>
          <p className="font-semibold text-foreground">Нет организаций</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Попросите администратора пригласить вас в организацию
          </p>
        </div>
      </motion.div>
    );
  }

  // ── Selection ─────────────────────────────────────────────────────────────
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-8 px-4">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex flex-col items-center gap-2 text-center"
      >
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Выберите организацию
        </h1>
        <p className="text-sm text-muted-foreground">
          Переключаться между организациями можно в любое время
        </p>
      </motion.div>

      {/* Auto-select banner */}
      <AnimatePresence>
        {autoSelecting && orgs.length === 1 && (
          <AutoSelectBanner key="auto" orgName={orgs[0].name} />
        )}
      </AnimatePresence>

      {/* Cards grid — 2 cols on sm+, 1 on mobile */}
      <div
        role="listbox"
        aria-label="Список организаций"
        className="grid w-full max-w-lg grid-cols-1 gap-4 sm:grid-cols-2"
      >
        {orgs.map((org, i) => (
          <OrgCard
            key={org.id}
            org={org}
            selected={selectedId === org.id}
            index={i}
            onSelect={() => handleSelect(org)}
          />
        ))}
      </div>

      {/* Keyboard hint — only when multiple orgs */}
      {orgs.length > 1 && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: orgs.length * 0.08 + 0.15 }}
          className="text-xs text-muted-foreground"
        >
          Используйте{" "}
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">
            ←→
          </kbd>{" "}
          /{" "}
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">
            ↑↓
          </kbd>{" "}
          для навигации и{" "}
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">
            Enter
          </kbd>{" "}
          для выбора
        </motion.p>
      )}
    </div>
  );
}
