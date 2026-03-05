"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Search } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useActiveOrg } from "@/hooks/use-active-org";
import {
  classifyQuery,
  useInternalSearch,
  useExternalSearch,
  type SearchRoute,
} from "@/hooks/use-search";
import { InternalResultsSection } from "@/components/search/InternalResultsSection";
import { ExternalResultsSection } from "@/components/search/ExternalResultsSection";
import { RouteIndicator } from "@/components/search/RouteIndicator";

export function SearchView() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";
  const [query, setQuery] = useState(initialQuery);
  const [route, setRoute] = useState<SearchRoute>(() =>
    initialQuery ? classifyQuery(initialQuery) : "both",
  );
  const { token } = useAuth();
  const { activeOrg } = useActiveOrg();
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const internal = useInternalSearch();
  const external = useExternalSearch();

  const executeSearch = useCallback(
    (q: string) => {
      const trimmed = q.trim();
      if (!trimmed || !token) return;

      const classified = classifyQuery(trimmed);
      setRoute(classified);

      if (
        (classified === "internal" || classified === "both") &&
        activeOrg
      ) {
        internal.mutate({ token, orgId: activeOrg.id, query: trimmed });
      }

      if (classified === "external" || classified === "both") {
        external.mutate({ token, query: trimmed });
      }
    },
    [token, activeOrg, internal, external],
  );

  const handleInputChange = useCallback(
    (value: string) => {
      setQuery(value);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        executeSearch(value);
      }, 300);
    },
    [executeSearch],
  );

  // Run search on mount if query param present
  useEffect(() => {
    if (initialQuery && token) {
      executeSearch(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, activeOrg?.id]);

  // Global "/" shortcut to focus search
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (
        e.key === "/" &&
        !e.metaKey &&
        !e.ctrlKey &&
        document.activeElement?.tagName !== "INPUT" &&
        document.activeElement?.tagName !== "TEXTAREA" &&
        !document.activeElement?.getAttribute("contenteditable")
      ) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  const hasQuery = query.trim().length > 0;
  const hasResults =
    (internal.data && internal.data.length > 0) ||
    (external.data && external.data.results.length > 0);
  const isSearching = internal.isPending || external.isPending;

  return (
    <div className="space-y-6">
      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#6b6b80]" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => handleInputChange(e.target.value)}
          placeholder="Search across your knowledge base and the web..."
          autoFocus
          className="w-full rounded-xl border border-[#2a2a3e] bg-[#14141f] py-4 pl-12 pr-4 text-lg text-[#e2e2e8] placeholder-[#45455a] outline-none transition-colors focus:border-[#7c5cfc40] focus:ring-1 focus:ring-[#7c5cfc40]"
        />
        {hasQuery && <RouteIndicator route={route} />}
      </div>

      {/* Empty state */}
      {!hasQuery && !hasResults && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Search className="mb-4 h-12 w-12 text-[#45455a]" />
          <p className="text-lg text-[#6b6b80]">
            Start typing to search across your knowledge base and the web
          </p>
          <p className="mt-2 text-sm text-[#45455a]">
            Press <kbd className="rounded border border-[#2a2a3e] bg-[#1a1a2e] px-1.5 py-0.5 font-mono text-xs text-[#6b6b80]">/</kbd> to focus search
          </p>
        </div>
      )}

      {/* Results grid */}
      {hasQuery && (
        <div className="grid gap-6 lg:grid-cols-2">
          {(route === "internal" || route === "both") && (
            <InternalResultsSection
              results={internal.data ?? []}
              isLoading={internal.isPending}
              error={internal.error?.message ?? null}
            />
          )}
          {(route === "external" || route === "both") && (
            <ExternalResultsSection
              results={external.data?.results ?? []}
              isLoading={external.isPending}
              error={external.error?.message ?? null}
            />
          )}
        </div>
      )}

      {/* No results */}
      {hasQuery && !isSearching && !hasResults && (internal.data || external.data) && (
        <div className="py-12 text-center">
          <p className="text-[#6b6b80]">No results found for &ldquo;{query.trim()}&rdquo;</p>
        </div>
      )}
    </div>
  );
}
