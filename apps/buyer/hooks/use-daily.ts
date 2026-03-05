import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  daily as dailyApi,
  missions as missionsApi,
} from "@/lib/api";

export function useDailySummary(token: string | null) {
  return useQuery({
    queryKey: ["daily", "summary"],
    queryFn: () => dailyApi.getSummary(token!),
    enabled: !!token,
    staleTime: 60 * 1000,
  });
}

export function useStartMission(token: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (missionId: string) => missionsApi.start(token!, missionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["daily", "summary"] });
    },
  });
}

export function useCompleteMission(token: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ missionId, sessionId }: { missionId: string; sessionId: string }) =>
      missionsApi.complete(token!, missionId, sessionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["daily", "summary"] });
      qc.invalidateQueries({ queryKey: ["missions", "history"] });
    },
  });
}

export function useMissionHistory(token: string | null, limit: number = 5) {
  return useQuery({
    queryKey: ["missions", "history", limit],
    queryFn: () => missionsApi.getHistory(token!, { limit }),
    enabled: !!token,
  });
}
