import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  coach as coachApi,
  missions as missionsApi,
  type CoachPhase,
  type CoachStartResponse,
  type CoachChatResponse,
  type CoachEndResponse,
} from "@/lib/api";

export type { CoachPhase };

export interface CoachMessage {
  role: "user" | "coach";
  content: string;
  phase?: CoachPhase;
}

export function useStartCoachSession(token: string | null) {
  return useMutation({
    mutationFn: (missionId: string) => coachApi.startSession(token!, missionId),
  });
}

export function useSendCoachMessage(token: string | null) {
  return useMutation({
    mutationFn: ({ sessionId, message }: { sessionId: string; message: string }) =>
      coachApi.sendMessage(token!, sessionId, message),
  });
}

export function useEndCoachSession(token: string | null) {
  return useMutation({
    mutationFn: (sessionId: string) => coachApi.endSession(token!, sessionId),
  });
}

export function useCompleteMissionWithCoach(token: string | null) {
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
