"use client";

import type { SearchRoute } from "@/hooks/use-search";

const ROUTE_LABELS: Record<SearchRoute, string> = {
  internal: "Internal only",
  external: "External only",
  both: "Internal + External",
};

export function RouteIndicator({ route }: { route: SearchRoute }) {
  return (
    <span className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full border border-[#2a2a3e] bg-[#1a1a2e] px-3 py-1 text-xs text-[#6b6b80]">
      {(route === "internal" || route === "both") && (
        <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-[#7c5cfc]" />
      )}
      {(route === "external" || route === "both") && (
        <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-[#38bdf8]" />
      )}
      {ROUTE_LABELS[route]}
    </span>
  );
}
