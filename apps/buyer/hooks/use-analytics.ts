"use client";

import { useQuery } from "@tanstack/react-query";
import { trustLevels, type TrustLevelWithUser } from "@/lib/api";

// ---------- Types ----------

export interface TeamMemberAnalytics {
  user_id: string;
  level: number;
  total_missions_completed: number;
  total_concepts_mastered: number;
  unlocked_areas: string[];
}

export interface ConceptNode {
  id: string;
  name: string;
}

export interface ConceptEdge {
  source: string;
  target: string;
}

export interface OrgConceptsResponse {
  nodes: ConceptNode[];
  edges: ConceptEdge[];
}

export type MasteryStatus = "mastered" | "learning" | "not_started";

export interface MemberConceptStatus {
  user_id: string;
  concept_id: string;
  status: MasteryStatus;
}

export interface ConceptCoverageData {
  concepts: ConceptNode[];
  members: { user_id: string; level: number }[];
  matrix: MemberConceptStatus[][];
}

export interface BottleneckItem {
  concept_id: string;
  concept_name: string;
  stuck_count: number;
  total_members: number;
  stuck_percentage: number;
}

export interface TeamOverviewStats {
  total_members: number;
  avg_trust_level: number;
  active_today: number;
  completion_rate: number;
  distribution: { level: number; label: string; count: number }[];
}

// ---------- Level names ----------

const LEVEL_LABELS: Record<number, string> = {
  0: "Newcomer",
  1: "Explorer",
  2: "Contributor",
  3: "Master",
  4: "Expert",
  5: "Mentor",
};

// ---------- Aggregation ----------

function aggregateOverview(levels: TrustLevelWithUser[]): TeamOverviewStats {
  const total = levels.length;
  if (total === 0) {
    return {
      total_members: 0,
      avg_trust_level: 0,
      active_today: 0,
      completion_rate: 0,
      distribution: [],
    };
  }

  const avg = levels.reduce((sum, m) => sum + m.level, 0) / total;

  // Simulate active today as members with at least 1 mission
  const activeToday = levels.filter((m) => m.total_missions_completed > 0).length;

  // Completion rate = % of members who reached level >= 2
  const completed = levels.filter((m) => m.level >= 2).length;
  const completionRate = (completed / total) * 100;

  // Distribution counts per level
  const counts = new Map<number, number>();
  for (const m of levels) {
    counts.set(m.level, (counts.get(m.level) ?? 0) + 1);
  }

  const distribution = Array.from({ length: 6 }, (_, i) => ({
    level: i,
    label: LEVEL_LABELS[i] ?? `Lvl ${i}`,
    count: counts.get(i) ?? 0,
  }));

  return {
    total_members: total,
    avg_trust_level: Math.round(avg * 10) / 10,
    active_today: activeToday,
    completion_rate: Math.round(completionRate),
    distribution,
  };
}

function buildConceptCoverage(
  members: TrustLevelWithUser[],
  conceptNodes: ConceptNode[],
): ConceptCoverageData {
  // Simulate concept mastery status based on member level and concept index
  // In production, this would come from actual mastery data
  const matrix: MemberConceptStatus[][] = conceptNodes.map((concept, ci) =>
    members.map((member) => {
      let status: MasteryStatus = "not_started";
      // Higher-level members have more mastered concepts
      const threshold = member.level / 5;
      const conceptDifficulty = ci / conceptNodes.length;

      if (conceptDifficulty < threshold * 0.8) {
        status = "mastered";
      } else if (conceptDifficulty < threshold * 1.2) {
        status = "learning";
      }

      return {
        user_id: member.user_id,
        concept_id: concept.id,
        status,
      };
    }),
  );

  return {
    concepts: conceptNodes,
    members: members.map((m) => ({ user_id: m.user_id, level: m.level })),
    matrix,
  };
}

function findBottlenecks(coverage: ConceptCoverageData): BottleneckItem[] {
  const totalMembers = coverage.members.length;
  if (totalMembers === 0) return [];

  const bottlenecks: BottleneckItem[] = [];

  for (let ci = 0; ci < coverage.concepts.length; ci++) {
    const row = coverage.matrix[ci];
    const stuckCount = row.filter(
      (cell) => cell.status === "not_started" || cell.status === "learning",
    ).length;
    const pct = (stuckCount / totalMembers) * 100;

    if (pct > 50) {
      bottlenecks.push({
        concept_id: coverage.concepts[ci].id,
        concept_name: coverage.concepts[ci].name,
        stuck_count: stuckCount,
        total_members: totalMembers,
        stuck_percentage: Math.round(pct),
      });
    }
  }

  return bottlenecks.sort((a, b) => b.stuck_percentage - a.stuck_percentage);
}

// ---------- Mock concept data (until real API exists) ----------

function mockOrgConcepts(): OrgConceptsResponse {
  const names = [
    "TypeScript Basics",
    "React Hooks",
    "State Management",
    "REST API Design",
    "Database Modeling",
    "Authentication",
    "Testing Strategy",
    "CI/CD Pipelines",
    "Docker Containers",
    "Kubernetes Basics",
    "Monitoring",
    "Security Best Practices",
  ];

  const nodes: ConceptNode[] = names.map((name, i) => ({
    id: `concept-${i}`,
    name,
  }));

  const edges: ConceptEdge[] = [
    { source: "concept-0", target: "concept-1" },
    { source: "concept-1", target: "concept-2" },
    { source: "concept-3", target: "concept-5" },
    { source: "concept-6", target: "concept-7" },
    { source: "concept-8", target: "concept-9" },
  ];

  return { nodes, edges };
}

// ---------- Hooks ----------

export function useTeamOverview(token: string | null, orgId: string | null) {
  return useQuery({
    queryKey: ["analytics", "team-overview", orgId],
    queryFn: async () => {
      const response = await trustLevels.getOrgLevels(token!, orgId!, {
        limit: 200,
      });
      return aggregateOverview(response.levels);
    },
    enabled: !!token && !!orgId,
  });
}

export function useTeamMembers(token: string | null, orgId: string | null) {
  return useQuery({
    queryKey: ["analytics", "team-members", orgId],
    queryFn: async () => {
      const response = await trustLevels.getOrgLevels(token!, orgId!, {
        limit: 200,
      });
      return response.levels;
    },
    enabled: !!token && !!orgId,
  });
}

export function useOrgConcepts(_token: string | null, orgId: string | null) {
  return useQuery({
    queryKey: ["analytics", "org-concepts", orgId],
    queryFn: () => {
      // Mock until RAG endpoint GET /kb/{org_id}/concepts is available
      return Promise.resolve(mockOrgConcepts());
    },
    enabled: !!_token && !!orgId,
  });
}

export function useConceptCoverage(
  token: string | null,
  orgId: string | null,
) {
  const { data: members } = useTeamMembers(token, orgId);
  const { data: concepts } = useOrgConcepts(token, orgId);

  return useQuery({
    queryKey: ["analytics", "concept-coverage", orgId],
    queryFn: () => {
      return Promise.resolve(buildConceptCoverage(members!, concepts!.nodes));
    },
    enabled: !!members && !!concepts,
  });
}

export function useBottlenecks(token: string | null, orgId: string | null) {
  const { data: coverage } = useConceptCoverage(token, orgId);

  return useQuery({
    queryKey: ["analytics", "bottlenecks", orgId],
    queryFn: () => {
      return Promise.resolve(findBottlenecks(coverage!));
    },
    enabled: !!coverage,
  });
}
