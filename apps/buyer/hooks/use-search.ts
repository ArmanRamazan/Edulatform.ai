import { useMutation } from "@tanstack/react-query";
import {
  kb,
  externalSearch,
  type KbSearchResult,
  type ExternalSearchResult,
} from "@/lib/api";

export type SearchRoute = "internal" | "external" | "both";

const INTERNAL_SIGNALS = [
  "наш",
  "наша",
  "наши",
  "нашей",
  "нашем",
  "у нас",
  "internal",
  "наша команда",
  "наш проект",
  "нашу",
];

const EXTERNAL_SIGNALS = [
  "react",
  "python",
  "docker",
  "kubernetes",
  "typescript",
  "javascript",
  "rust",
  "golang",
  "java",
  "how to",
  "best practice",
  "best practices",
  "tutorial",
  "example",
  "documentation",
  "docs",
  "npm",
  "pip",
  "cargo",
  "webpack",
  "vite",
  "nextjs",
  "next.js",
  "fastapi",
  "django",
  "flask",
  "aws",
  "gcp",
  "azure",
  "redis",
  "postgres",
  "mongodb",
];

export function classifyQuery(query: string): SearchRoute {
  const lower = query.toLowerCase().trim();
  if (!lower) return "both";

  const hasInternal = INTERNAL_SIGNALS.some((s) => lower.includes(s));
  const hasExternal = EXTERNAL_SIGNALS.some((s) => lower.includes(s));

  if (hasInternal && !hasExternal) return "internal";
  if (hasExternal && !hasInternal) return "external";
  return "both";
}

export function useInternalSearch() {
  return useMutation({
    mutationFn: ({
      token,
      orgId,
      query,
      limit,
    }: {
      token: string;
      orgId: string;
      query: string;
      limit?: number;
    }) => kb.search(token, orgId, query, limit),
  });
}

export function useExternalSearch() {
  return useMutation({
    mutationFn: ({
      token,
      query,
      limit,
    }: {
      token: string;
      query: string;
      limit?: number;
    }) => externalSearch.search(token, query, limit),
  });
}

export interface SmartSearchState {
  route: SearchRoute;
  internalResults: KbSearchResult[];
  externalResults: ExternalSearchResult[];
  internalLoading: boolean;
  externalLoading: boolean;
  internalError: string | null;
  externalError: string | null;
}
