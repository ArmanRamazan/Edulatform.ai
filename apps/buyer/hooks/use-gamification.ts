import { useQuery } from "@tanstack/react-query";
import { xp as xpApi, badges as badgesApi, streaks as streaksApi } from "@/lib/api";

export function useMyXp(token: string | null) {
  return useQuery({
    queryKey: ["xp", "me"],
    queryFn: () => xpApi.me(token!, { limit: 1 }),
    enabled: !!token,
    select: (data) => data.total_xp,
  });
}

export function useMyXpHistory(token: string | null, params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ["xp", "history", params],
    queryFn: () => xpApi.me(token!, params),
    enabled: !!token,
  });
}

export function useMyBadges(token: string | null) {
  return useQuery({
    queryKey: ["badges", "me"],
    queryFn: () => badgesApi.me(token!),
    enabled: !!token,
  });
}

export function useMyStreak(token: string | null) {
  return useQuery({
    queryKey: ["streaks", "me"],
    queryFn: () => streaksApi.me(token!),
    enabled: !!token,
  });
}
