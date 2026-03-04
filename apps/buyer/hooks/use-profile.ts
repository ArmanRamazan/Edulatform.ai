import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { profiles, type FollowCounts } from "@/lib/api";

export function useUserProfile(userId: string) {
  return useQuery({
    queryKey: ["profile", userId],
    queryFn: () => profiles.get(userId),
    staleTime: 60_000,
  });
}

export function useFollowCounts(userId: string) {
  return useQuery({
    queryKey: ["followCounts", userId],
    queryFn: () => profiles.followCounts(userId),
  });
}

export function useMyFollowing(token: string | null) {
  return useQuery({
    queryKey: ["following", "me"],
    queryFn: () => profiles.myFollowing(token!, { limit: 100 }),
    enabled: !!token,
  });
}

export function useFollowUser(token: string | null, userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => profiles.follow(token!, userId),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["followCounts", userId] });
      await queryClient.cancelQueries({ queryKey: ["following", "me"] });
      const previousCounts = queryClient.getQueryData<FollowCounts>(["followCounts", userId]);
      if (previousCounts) {
        queryClient.setQueryData<FollowCounts>(["followCounts", userId], {
          ...previousCounts,
          followers_count: previousCounts.followers_count + 1,
        });
      }
      return { previousCounts };
    },
    onError: (_err, _vars, context) => {
      if (context?.previousCounts) {
        queryClient.setQueryData(["followCounts", userId], context.previousCounts);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["followCounts", userId] });
      queryClient.invalidateQueries({ queryKey: ["following", "me"] });
    },
  });
}

export function useUnfollowUser(token: string | null, userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => profiles.unfollow(token!, userId),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["followCounts", userId] });
      await queryClient.cancelQueries({ queryKey: ["following", "me"] });
      const previousCounts = queryClient.getQueryData<FollowCounts>(["followCounts", userId]);
      if (previousCounts) {
        queryClient.setQueryData<FollowCounts>(["followCounts", userId], {
          ...previousCounts,
          followers_count: Math.max(0, previousCounts.followers_count - 1),
        });
      }
      return { previousCounts };
    },
    onError: (_err, _vars, context) => {
      if (context?.previousCounts) {
        queryClient.setQueryData(["followCounts", userId], context.previousCounts);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["followCounts", userId] });
      queryClient.invalidateQueries({ queryKey: ["following", "me"] });
    },
  });
}
