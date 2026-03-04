import { useQuery } from "@tanstack/react-query";
import { velocity as velocityApi } from "@/lib/api";

export function useMyVelocity(token: string | null) {
  return useQuery({
    queryKey: ["velocity", "me"],
    queryFn: () => velocityApi.me(token!),
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
  });
}
