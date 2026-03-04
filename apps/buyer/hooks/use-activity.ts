import { useQuery } from "@tanstack/react-query";
import { activity as activityApi } from "@/lib/api";

export function useMyActivity(token: string | null, params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ["activity", "me", params],
    queryFn: () => activityApi.me(token!, params),
    enabled: !!token,
  });
}

export function useSocialFeed(
  token: string | null,
  userIds: string[],
  params?: { limit?: number; offset?: number },
) {
  return useQuery({
    queryKey: ["activity", "feed", userIds, params],
    queryFn: () => activityApi.feed(token!, { user_ids: userIds, ...params }),
    enabled: !!token && userIds.length > 0,
  });
}
