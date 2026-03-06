"use client";

import { useQuery } from "@tanstack/react-query";
import {
  kb,
  missions as missionsApi,
  trustLevels,
  type KbSearchResult,
  type Mission,
  type TrustLevelWithUser,
} from "@/lib/api";

// ---------- Internal Sources ----------

export function useConceptSources(
  token: string | null,
  orgId: string | null,
  conceptName: string,
) {
  return useQuery({
    queryKey: ["concept-hub", "sources", orgId, conceptName],
    queryFn: () => kb.search(token!, orgId!, conceptName, 10),
    enabled: !!token && !!orgId && conceptName.length > 0,
    staleTime: 5 * 60 * 1000,
  });
}

// ---------- Missions for concept ----------

export function useConceptMissions(
  token: string | null,
  conceptId: string,
) {
  return useQuery<Mission[]>({
    queryKey: ["concept-hub", "missions", conceptId],
    queryFn: async () => {
      const result = await missionsApi.getHistory(token!, { limit: 50 });
      return result.items.filter((m) => m.concept_id === conceptId);
    },
    enabled: !!token && conceptId.length > 0,
    staleTime: 2 * 60 * 1000,
  });
}

// ---------- Team mastery (admin only) ----------

export function useConceptTeamMastery(
  token: string | null,
  orgId: string | null,
  isAdmin: boolean,
) {
  return useQuery<TrustLevelWithUser[]>({
    queryKey: ["concept-hub", "team-mastery", orgId],
    queryFn: async () => {
      const result = await trustLevels.getOrgLevels(token!, orgId!, {
        limit: 100,
      });
      return result.levels;
    },
    enabled: !!token && !!orgId && isAdmin,
    staleTime: 5 * 60 * 1000,
  });
}
