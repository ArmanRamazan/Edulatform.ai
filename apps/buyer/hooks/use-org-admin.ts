"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { organizations, type OrgMember } from "@/lib/api";
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
    onMutate: async (userId: string) => {
      await queryClient.cancelQueries({ queryKey: ["organizations", orgId, "members"] });
      const previous = queryClient.getQueryData<OrgMember[]>([
        "organizations",
        orgId,
        "members",
      ]);
      queryClient.setQueryData<OrgMember[]>(
        ["organizations", orgId, "members"],
        (old) => old?.filter((m) => m.user_id !== userId) ?? [],
      );
      return { previous };
    },
    onError: (_err, _userId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["organizations", orgId, "members"], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations", orgId, "members"] });
    },
  });
}
