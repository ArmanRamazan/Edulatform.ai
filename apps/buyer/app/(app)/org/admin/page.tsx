"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Building2,
  Users,
  UserPlus,
  Trash2,
  Shield,
  ShieldCheck,
  AlertTriangle,
  Crown,
  CheckCircle2,
  Loader2,
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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

function RoleBadge({ role }: { role: string }) {
  const isAdmin = role === "admin" || role === "owner";
  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1 text-xs font-medium",
        isAdmin
          ? "border-violet-500/40 bg-violet-500/10 text-violet-300"
          : "border-zinc-600/40 bg-zinc-800/50 text-zinc-400",
      )}
    >
      {isAdmin ? <ShieldCheck className="h-3 w-3" /> : <Shield className="h-3 w-3" />}
      {role}
    </Badge>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Remove confirmation dialog
// ─────────────────────────────────────────────────────────────────────────────

interface RemoveDialogProps {
  member: OrgMember | null;
  orgId: string;
  onClose: () => void;
}

function RemoveDialog({ member, orgId, onClose }: RemoveDialogProps) {
  const removeMutation = useRemoveMember(orgId);

  async function handleConfirm() {
    if (!member) return;
    await removeMutation.mutateAsync(member.user_id);
    onClose();
  }

  return (
    <Dialog open={!!member} onOpenChange={onClose}>
      <DialogContent className="border-zinc-800 bg-[#1a1a1f] sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-white">
            <AlertTriangle className="h-5 w-5 text-red-400" />
            Удалить участника?
          </DialogTitle>
          <DialogDescription className="text-zinc-400">
            Пользователь{" "}
            <span className="font-mono text-xs text-zinc-300">
              {member?.user_id.slice(0, 8)}…
            </span>{" "}
            потеряет доступ к организации. Это действие необратимо.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={onClose}
            className="border-zinc-700 bg-transparent text-zinc-300 hover:bg-zinc-800"
          >
            Отмена
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={removeMutation.isPending}
            className="gap-2"
          >
            {removeMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
            Удалить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Invite form
// ─────────────────────────────────────────────────────────────────────────────

interface InviteFormProps {
  orgId: string;
}

function InviteForm({ orgId }: InviteFormProps) {
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState("member");
  const [success, setSuccess] = useState(false);
  const inviteMutation = useInviteMember(orgId);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!userId.trim()) return;
    await inviteMutation.mutateAsync({ user_id: userId.trim(), role });
    setUserId("");
    setRole("member");
    setSuccess(true);
    setTimeout(() => setSuccess(false), 3000);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <div className="flex flex-1 flex-col gap-1.5">
        <label className="text-xs font-medium text-zinc-400">User ID</label>
        <Input
          placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          className="border-zinc-700 bg-zinc-900/50 font-mono text-sm text-zinc-100 placeholder:text-zinc-600 focus-visible:ring-violet-500/50"
          disabled={inviteMutation.isPending}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-medium text-zinc-400">Роль</label>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          disabled={inviteMutation.isPending}
          className="h-9 rounded-md border border-zinc-700 bg-zinc-900/50 px-3 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50 disabled:opacity-50"
        >
          <option value="member">member</option>
          <option value="admin">admin</option>
          <option value="viewer">viewer</option>
        </select>
      </div>
      <Button
        type="submit"
        disabled={inviteMutation.isPending || !userId.trim()}
        className="gap-2 bg-violet-600 text-white hover:bg-violet-500 disabled:opacity-50"
      >
        {inviteMutation.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : success ? (
          <CheckCircle2 className="h-4 w-4" />
        ) : (
          <UserPlus className="h-4 w-4" />
        )}
        {success ? "Добавлен" : "Добавить"}
      </Button>
      {inviteMutation.isError && (
        <p className="text-xs text-red-400">{(inviteMutation.error as Error).message}</p>
      )}
    </form>
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
  const initial = member.user_id.charAt(0).toUpperCase();
  return (
    <motion.tr
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.04 }}
      className="group border-b border-zinc-800/50 last:border-0"
    >
      <td className="py-3 pl-4 pr-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-violet-500/15 text-sm font-semibold text-violet-300">
            {initial}
          </div>
          <span className="font-mono text-xs text-zinc-400">
            {member.user_id}
          </span>
        </div>
      </td>
      <td className="py-3 px-3">
        <RoleBadge role={member.role} />
      </td>
      <td className="py-3 px-3 text-xs text-zinc-500">
        {formatDate(member.joined_at)}
      </td>
      <td className="py-3 pl-3 pr-4 text-right">
        <button
          onClick={() => onRemove(member)}
          className="rounded-md p-1.5 text-zinc-600 opacity-0 transition-all hover:bg-red-500/10 hover:text-red-400 group-hover:opacity-100"
          aria-label="Remove member"
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

export function OrgAdminPage() {
  const { activeOrg } = useActiveOrg();
  const { token } = useAuth();
  const orgId = activeOrg?.id ?? null;

  const orgQuery = useOrganization(token, orgId);
  const membersQuery = useOrgMembers(orgId);

  const [memberToRemove, setMemberToRemove] = useState<OrgMember | null>(null);

  const org = orgQuery.data;
  const members = membersQuery.data ?? [];
  const planTier = (org?.settings?.plan_tier as string | undefined) ?? "free";

  if (!activeOrg) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-sm text-zinc-500">Организация не выбрана</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 py-2">
      {/* ── Page header ── */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h1 className="text-xl font-semibold text-white">Управление организацией</h1>
        <p className="mt-0.5 text-sm text-zinc-500">
          Участники, роли и настройки
        </p>
      </motion.div>

      {/* ── Org overview ── */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05 }}
      >
        <Card className="border-zinc-800 bg-[#1a1a1f] p-5">
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
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-violet-500/15 text-xl font-bold text-violet-300">
                {org?.name.charAt(0).toUpperCase() ?? "?"}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-lg font-semibold text-white">{org?.name}</h2>
                  <Badge
                    variant="outline"
                    className="border-violet-500/30 bg-violet-500/10 text-xs text-violet-300"
                  >
                    <Crown className="mr-1 h-3 w-3" />
                    {planTier}
                  </Badge>
                  {org?.is_active === false && (
                    <Badge variant="outline" className="border-red-500/30 text-xs text-red-400">
                      неактивна
                    </Badge>
                  )}
                </div>
                <p className="mt-0.5 font-mono text-xs text-zinc-500">
                  /{org?.slug}
                </p>
              </div>

              {/* Stats */}
              <div className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-2">
                <Users className="h-4 w-4 text-zinc-500" />
                {membersQuery.isLoading ? (
                  <Skeleton className="h-4 w-8" />
                ) : (
                  <span className="text-sm font-medium text-zinc-300">
                    {members.length}
                  </span>
                )}
                <span className="text-xs text-zinc-500">участников</span>
              </div>
            </div>
          )}
        </Card>
      </motion.div>

      {/* ── Members section ── */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="space-y-3"
      >
        <div className="flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-medium text-zinc-300">
            <Users className="h-4 w-4 text-zinc-500" />
            Участники
          </h3>
          <span className="text-xs text-zinc-600">{members.length} всего</span>
        </div>

        <Card className="border-zinc-800 bg-[#1a1a1f] overflow-hidden">
          {membersQuery.isLoading ? (
            <div className="divide-y divide-zinc-800/50">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3">
                  <Skeleton className="h-8 w-8 rounded-full" />
                  <Skeleton className="h-4 w-64" />
                  <Skeleton className="ml-auto h-5 w-16" />
                </div>
              ))}
            </div>
          ) : membersQuery.isError ? (
            <div className="flex items-center gap-2 px-4 py-6 text-sm text-red-400">
              <AlertTriangle className="h-4 w-4" />
              Не удалось загрузить участников
            </div>
          ) : members.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-10 text-zinc-600">
              <Building2 className="h-8 w-8 opacity-40" />
              <p className="text-sm">Нет участников</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[540px] text-sm">
                <thead>
                  <tr className="border-b border-zinc-800 text-left">
                    <th className="py-2.5 pl-4 pr-3 text-xs font-medium text-zinc-500">
                      User ID
                    </th>
                    <th className="py-2.5 px-3 text-xs font-medium text-zinc-500">
                      Роль
                    </th>
                    <th className="py-2.5 px-3 text-xs font-medium text-zinc-500">
                      Вступил
                    </th>
                    <th className="py-2.5 pl-3 pr-4" />
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence>
                    {members.map((member, i) => (
                      <MemberRow
                        key={member.id}
                        member={member}
                        index={i}
                        onRemove={setMemberToRemove}
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
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.15 }}
        className="space-y-3"
      >
        <h3 className="flex items-center gap-2 text-sm font-medium text-zinc-300">
          <UserPlus className="h-4 w-4 text-zinc-500" />
          Добавить участника
        </h3>
        <Card className="border-zinc-800 bg-[#1a1a1f] p-4">
          <InviteForm orgId={activeOrg.id} />
        </Card>
      </motion.div>

      {/* ── Remove confirmation dialog ── */}
      <RemoveDialog
        member={memberToRemove}
        orgId={activeOrg.id}
        onClose={() => setMemberToRemove(null)}
      />
    </div>
  );
}
