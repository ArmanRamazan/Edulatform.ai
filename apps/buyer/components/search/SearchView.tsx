"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Search, SearchX } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
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
        <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => handleInputChange(e.target.value)}
          placeholder="Search across your knowledge base and the web..."
          autoFocus
          className="w-full rounded-xl border border-border bg-card py-4 pl-12 pr-4 text-lg text-foreground placeholder:text-muted-foreground/50 outline-none transition-colors focus:border-primary/30 focus:ring-1 focus:ring-primary/20"
        />
        {hasQuery && <RouteIndicator route={route} />}
      </div>

      {/* Empty state — before first query */}
      <AnimatePresence>
        {!hasQuery && !hasResults && (
          <motion.div
            key="search-idle"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col items-center justify-center py-24 text-center"
          >
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/8 ring-1 ring-primary/15">
              <Search className="h-6 w-6 text-muted-foreground/50" aria-hidden="true" />
            </div>
            <p className="text-base text-muted-foreground">
              Search across your knowledge base and the web
            </p>
            <p className="mt-2 text-sm text-muted-foreground/50">
              Press{" "}
              <kbd className="rounded border border-border bg-secondary px-1.5 py-0.5 font-mono text-xs text-muted-foreground">
                /
              </kbd>{" "}
              to focus search
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results grid */}
      {hasQuery && (
        <div className="grid gap-6 lg:grid-cols-2">
          {(route === "internal" || route === "both") && (
            <InternalResultsSection
              results={internal.data ?? []}
              isLoading={internal.isPending}
              error={internal.error?.message ?? null}
              onRetry={() => executeSearch(query)}
            />
          )}
          {(route === "external" || route === "both") && (
            <ExternalResultsSection
              results={external.data?.results ?? []}
              isLoading={external.isPending}
              error={external.error?.message ?? null}
              onRetry={() => executeSearch(query)}
            />
          )}
        </div>
      )}

      {/* No results */}
      {hasQuery && !isSearching && !hasResults && (internal.data || external.data) && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className="flex flex-col items-center gap-3 py-16 text-center"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary ring-1 ring-border">
            <SearchX
              className="h-5 w-5 text-muted-foreground/50"
              aria-hidden="true"
              strokeWidth={1.5}
            />
          </div>
          <div>
            <p className="text-sm font-medium text-muted-foreground">No results found</p>
            <p className="mt-0.5 text-xs text-muted-foreground/60">
              No results for &ldquo;{query.trim()}&rdquo;
            </p>
          </div>
        </motion.div>
      )}
    </div>
  );
}
