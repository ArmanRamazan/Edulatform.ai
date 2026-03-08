"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Building2,
  Users,
  UserPlus,
  Trash2,
  Shield,
  ShieldCheck,
  AlertCircle,
  Crown,
  CheckCircle2,
  Loader2,
  Undo2,
  RotateCcw,
} from "lucide-react";
import { useActiveOrg } from "@/hooks/use-active-org";
import { useAuth } from "@/hooks/use-auth";
import { useOrganization } from "@/hooks/use-organizations";
import { useOrgMembers, useInviteMember, useRemoveMember } from "@/hooks/use-org-admin";
import { type OrgMember } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return "сегодня";
  if (days === 1) return "вчера";
  if (days < 30) return `${days}д назад`;
  return formatDate(iso);
}

/** Deterministic accent from user_id so each avatar has its own colour */
const AVATAR_PALETTE = [
  "bg-primary/15 text-primary",
  "bg-[#34d399]/15 text-[#34d399]",
  "bg-[#38bdf8]/15 text-[#38bdf8]",
  "bg-[#fbbf24]/15 text-[#fbbf24]",
  "bg-[#f87171]/15 text-[#f87171]",
] as const;

function avatarClass(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  return AVATAR_PALETTE[hash % AVATAR_PALETTE.length];
}

/** Show first-4 … last-4 chars of UUID for readable truncation */
function truncateId(id: string): string {
  if (id.length <= 12) return id;
  return `${id.slice(0, 4)}…${id.slice(-4)}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// RoleBadge
// ─────────────────────────────────────────────────────────────────────────────

function RoleBadge({ role }: { role: string }) {
  const isElevated = role === "admin" || role === "owner";
  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1 text-xs font-medium",
        isElevated
          ? "border-primary/40 bg-primary/10 text-primary"
          : "border-border bg-muted/50 text-muted-foreground",
      )}
    >
      {isElevated ? <ShieldCheck className="h-3 w-3" /> : <Shield className="h-3 w-3" />}
      {role}
    </Badge>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Invite form
// ─────────────────────────────────────────────────────────────────────────────

interface InviteFormProps {
  orgId: string;
  inputRef: React.RefObject<HTMLInputElement | null>;
}

function InviteForm({ orgId, inputRef }: InviteFormProps) {
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState("member");
  const [successUserId, setSuccessUserId] = useState<string | null>(null);
  const inviteMutation = useInviteMember(orgId);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = userId.trim();
    if (!trimmed) return;
    await inviteMutation.mutateAsync({ user_id: trimmed, role });
    setSuccessUserId(trimmed);
    setUserId("");
    setRole("member");
    setTimeout(() => setSuccessUserId(null), 4000);
  }

  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex flex-1 flex-col gap-1.5">
          <label className="text-xs font-medium text-muted-foreground">User ID</label>
          <Input
            ref={inputRef}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            className="border-border bg-background/50 font-mono text-sm text-foreground placeholder:text-muted-foreground focus-visible:ring-primary/50"
            disabled={inviteMutation.isPending}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="invite-role"
            className="text-xs font-medium text-muted-foreground"
          >
            Роль
          </label>
          <select
            id="invite-role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            disabled={inviteMutation.isPending}
            aria-label="Выбрать роль участника"
            className="h-9 rounded-lg border border-border bg-background/50 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
          >
            <option value="viewer">viewer</option>
            <option value="member">member</option>
            <option value="admin">admin</option>
          </select>
        </div>
        <Button
          type="submit"
          disabled={inviteMutation.isPending || !userId.trim()}
          className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {inviteMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <UserPlus className="h-4 w-4" />
          )}
          Добавить
        </Button>
      </form>

      <AnimatePresence mode="wait">
        {successUserId ? (
          <motion.div
            key="success"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-2 rounded-lg border border-success/20 bg-success/5 px-3 py-2"
          >
            <CheckCircle2 className="h-4 w-4 shrink-0 text-success" />
            <span className="text-xs text-foreground/80">
              Участник{" "}
              <span className="font-mono text-xs text-foreground">
                {truncateId(successUserId)}
              </span>{" "}
              добавлен
            </span>
          </motion.div>
        ) : inviteMutation.isError ? (
          <motion.p
            key="error"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-1.5 text-xs text-destructive"
          >
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            {(inviteMutation.error as Error).message}
          </motion.p>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Member row
// ─────────────────────────────────────────────────────────────────────────────

interface MemberRowProps {
  member: OrgMember;
  index: number;
  onRemove: (m: OrgMember) => void;
}

function MemberRow({ member, index, onRemove }: MemberRowProps) {
  return (
    <motion.tr
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -8 }}
      transition={{ duration: 0.2, delay: Math.min(index * 0.04, 0.2) }}
      className="group border-b border-border/50 last:border-0 transition-colors hover:bg-muted/20"
    >
      <td className="py-3 pl-4 pr-3">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold uppercase",
              avatarClass(member.user_id),
            )}
          >
            {member.user_id.slice(0, 2)}
          </div>
          <span className="font-mono text-xs text-muted-foreground" title={member.user_id}>
            {truncateId(member.user_id)}
          </span>
        </div>
      </td>
      <td className="px-3 py-3">
        <RoleBadge role={member.role} />
      </td>
      <td className="hidden px-3 py-3 text-xs text-muted-foreground sm:table-cell">
        <span title={formatDate(member.joined_at)}>{formatRelative(member.joined_at)}</span>
      </td>
      <td className="py-3 pl-3 pr-4 text-right">
        <button
          onClick={() => onRemove(member)}
          className="rounded-md p-1.5 text-muted-foreground/40 opacity-0 transition-all hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive/50"
          aria-label={`Удалить участника ${truncateId(member.user_id)}`}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </td>
    </motion.tr>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────────────────────────────────────

export default function OrgAdminPage() {
  const { activeOrg } = useActiveOrg();
  const { token } = useAuth();
  const orgId = activeOrg?.id ?? null;

  const orgQuery = useOrganization(token, orgId);
  const membersQuery = useOrgMembers(orgId);
  const removeMutation = useRemoveMember(orgId ?? "");

  const [pendingRemoval, setPendingRemoval] = useState<OrgMember | null>(null);
  const pendingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inviteInputRef = useRef<HTMLInputElement | null>(null);

  const org = orgQuery.data;
  const members = membersQuery.data ?? [];
  const planTier = (org?.settings?.plan_tier as string | undefined) ?? "free";

  const displayedMembers = pendingRemoval
    ? members.filter((m) => m.user_id !== pendingRemoval.user_id)
    : members;

  function handleRemove(member: OrgMember) {
    if (pendingTimerRef.current !== null) {
      clearTimeout(pendingTimerRef.current);
      if (pendingRemoval) removeMutation.mutate(pendingRemoval.user_id);
    }
    setPendingRemoval(member);
    pendingTimerRef.current = setTimeout(() => {
      removeMutation.mutate(member.user_id);
      setPendingRemoval(null);
      pendingTimerRef.current = null;
    }, 5000);
  }

  function handleUndoRemove() {
    if (pendingTimerRef.current !== null) {
      clearTimeout(pendingTimerRef.current);
      pendingTimerRef.current = null;
    }
    setPendingRemoval(null);
  }

  useEffect(() => {
    return () => {
      if (pendingTimerRef.current !== null) clearTimeout(pendingTimerRef.current);
    };
  }, []);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.altKey && e.key === "i") {
        e.preventDefault();
        inviteInputRef.current?.focus();
        inviteInputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  if (!activeOrg) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex flex-col items-center gap-2 text-center">
          <Building2 className="h-8 w-8 text-muted-foreground/30" />
          <p className="text-sm text-muted-foreground">Организация не выбрана</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* ── Page header ── */}
      <motion.div
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
      >
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground">
              Управление организацией
            </h1>
            <p className="mt-0.5 text-sm text-muted-foreground">Участники, роли и настройки</p>
          </div>
          <button
            onClick={() => {
              inviteInputRef.current?.focus();
              inviteInputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
            }}
            className="flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 transition-colors"
            title="Alt+I"
          >
            <UserPlus className="h-3.5 w-3.5" />
            Добавить
          </button>
        </div>
      </motion.div>

      {/* ── Org overview card ── */}
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, delay: 0.05 }}
      >
        {orgQuery.isError ? (
          <Card className="border-border bg-card p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-destructive/10">
                <AlertCircle className="h-5 w-5 text-destructive" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-foreground">
                  Не удалось загрузить организацию
                </p>
                <p className="text-xs text-muted-foreground">
                  Проверьте подключение и попробуйте снова
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => orgQuery.refetch()}
                className="gap-1.5 border-border text-xs"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Повторить
              </Button>
            </div>
          </Card>
        ) : (
          <Card className="border-border bg-card p-5">
            {orgQuery.isLoading ? (
              <div className="flex items-center gap-4">
                <Skeleton className="h-12 w-12 rounded-xl" />
                <div className="space-y-2">
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-4 w-24" />
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-4">
                {/* Logo / initial */}
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-xl font-bold text-primary ring-1 ring-primary/20">
                  {org?.name.charAt(0).toUpperCase() ?? "?"}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-semibold tracking-tight text-foreground">
                      {org?.name}
                    </h2>
                    {org?.is_active === false && (
                      <Badge
                        variant="outline"
                        className="border-destructive/30 text-xs text-destructive"
                      >
                        неактивна
                      </Badge>
                    )}
                  </div>
                  <p className="mt-0.5 font-mono text-xs text-muted-foreground">/{org?.slug}</p>
                </div>

                {/* Stats pills */}
                <div className="flex flex-wrap gap-2">
                  <div className="flex items-center gap-1.5 rounded-lg border border-border bg-muted/30 px-3 py-1.5 text-xs">
                    <Crown className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="font-mono font-medium text-foreground">{planTier}</span>
                    <span className="text-muted-foreground">план</span>
                  </div>
                  <div className="flex items-center gap-1.5 rounded-lg border border-border bg-muted/30 px-3 py-1.5 text-xs">
                    <Users className="h-3.5 w-3.5 text-muted-foreground" />
                    {membersQuery.isLoading ? (
                      <Skeleton className="h-3 w-6" />
                    ) : (
                      <span className="font-mono font-medium text-foreground">
                        {members.length}
                      </span>
                    )}
                    <span className="text-muted-foreground">участников</span>
                  </div>
                </div>
              </div>
            )}
          </Card>
        )}
      </motion.div>

      {/* ── Members section ── */}
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, delay: 0.1 }}
        className="space-y-3"
      >
        <div className="flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-medium text-foreground/80">
            <Users className="h-4 w-4 text-muted-foreground" />
            Участники
          </h3>
          {members.length > 0 && (
            <span className="font-mono text-xs text-muted-foreground">{members.length}</span>
          )}
        </div>

        <Card className="overflow-hidden border-border bg-card">
          {membersQuery.isLoading ? (
            <div className="divide-y divide-border/50">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3">
                  <Skeleton className="h-8 w-8 rounded-full" />
                  <Skeleton className="h-4 w-48" />
                  <Skeleton className="ml-auto h-5 w-16" />
                </div>
              ))}
            </div>
          ) : membersQuery.isError ? (
            <div className="flex flex-col items-center justify-center gap-3 py-10">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-destructive/10">
                <AlertCircle className="h-5 w-5 text-destructive" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-foreground">
                  Не удалось загрузить участников
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">Проблема на стороне сервера</p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => membersQuery.refetch()}
                className="gap-1.5 border-border text-xs"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Попробовать снова
              </Button>
            </div>
          ) : displayedMembers.length === 0 && !pendingRemoval ? (
            <div className="flex flex-col items-center justify-center gap-2 py-14">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted/50">
                <Building2 className="h-6 w-6 text-muted-foreground/50" />
              </div>
              <div className="text-center">
                <p className="text-sm text-muted-foreground">Нет участников</p>
                <p className="text-xs text-muted-foreground/60">Добавьте первого участника ниже</p>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              {/* Undo banner */}
              <AnimatePresence>
                {pendingRemoval && (
                  <motion.div
                    key="undo-banner"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden border-b border-warning/20 bg-warning/5"
                  >
                    <div className="flex items-center gap-3 px-4 py-2.5">
                      <span className="flex-1 text-xs text-foreground/80">
                        Удаляем{" "}
                        <span className="font-mono text-xs text-foreground">
                          {truncateId(pendingRemoval.user_id)}
                        </span>
                      </span>
                      <button
                        onClick={handleUndoRemove}
                        autoFocus
                        className="flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium text-warning hover:bg-warning/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-warning/50 transition-colors"
                      >
                        <Undo2 className="h-3.5 w-3.5" />
                        Отменить
                      </button>
                      <div className="relative h-0.5 w-14 overflow-hidden rounded-full bg-border">
                        <motion.div
                          className="absolute inset-y-0 left-0 rounded-full bg-warning"
                          initial={{ width: "100%" }}
                          animate={{ width: "0%" }}
                          transition={{ duration: 5, ease: "linear" }}
                        />
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <table className="w-full min-w-[520px] text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/20">
                    <th className="py-2.5 pl-4 pr-3 text-left text-xs font-medium text-muted-foreground">
                      User ID
                    </th>
                    <th className="px-3 py-2.5 text-left text-xs font-medium text-muted-foreground">
                      Роль
                    </th>
                    <th className="hidden px-3 py-2.5 text-left text-xs font-medium text-muted-foreground sm:table-cell">
                      Вступил
                    </th>
                    <th className="py-2.5 pl-3 pr-4" />
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence initial={false}>
                    {displayedMembers.map((member, i) => (
                      <MemberRow
                        key={member.id}
                        member={member}
                        index={i}
                        onRemove={handleRemove}
                      />
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </motion.div>

      {/* ── Add member ── */}
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, delay: 0.15 }}
        className="space-y-3"
      >
        <h3 className="flex items-center gap-2 text-sm font-medium text-foreground/80">
          <UserPlus className="h-4 w-4 text-muted-foreground" />
          Добавить участника
          <kbd className="ml-1 rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground/60">
            Alt+I
          </kbd>
        </h3>
        <Card className="border-border bg-card p-4">
          <InviteForm orgId={activeOrg.id} inputRef={inviteInputRef} />
        </Card>
      </motion.div>
    </div>
  );
}
