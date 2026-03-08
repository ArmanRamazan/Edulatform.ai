"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { organizations } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";

export function useOrgMembers(orgId: string | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["organizations", orgId, "members"],
    queryFn: () => organizations.getMembers(token!, orgId!),
    enabled: !!token && !!orgId,
  });
}

export function useInviteMember(orgId: string) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { user_id: string; role: string }) =>
      organizations.addMember(token!, orgId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations", orgId, "members"] });
    },
  });
}

export function useRemoveMember(orgId: string) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => organizations.removeMember(token!, orgId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations", orgId, "members"] });
    },
  });
}
