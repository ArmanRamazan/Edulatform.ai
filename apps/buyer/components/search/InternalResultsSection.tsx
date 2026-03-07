"use client";

import { FileText, Code, Globe, File, AlertCircle, RefreshCw } from "lucide-react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import type { KbSearchResult } from "@/lib/api";

const SOURCE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  document: FileText,
  code: Code,
  web: Globe,
};

function SourceIcon({ sourceType }: { sourceType: string | null }) {
  const Icon = (sourceType && SOURCE_ICONS[sourceType]) || File;
  return <Icon className="h-4 w-4 shrink-0 text-[#7c5cfc]" />;
}

function truncateSnippet(content: string, maxLength: number = 200): string {
  if (content.length <= maxLength) return content;
  return content.slice(0, maxLength).trimEnd() + "...";
}

export function InternalResultsSection({
  results,
  isLoading,
  error,
  onRetry,
}: {
  results: KbSearchResult[];
  isLoading: boolean;
  error: string | null;
  onRetry?: () => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-[#7c5cfc]" />
        <h2 className="text-sm font-medium text-[#e2e2e8]">
          From your knowledge base
        </h2>
      </div>

      {/* Loading — shimmer that matches the card shape */}
      {isLoading && (
        <div className="space-y-3" aria-busy="true" aria-label="Searching knowledge base">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="overflow-hidden border-[#2a2a3e] bg-[#14141f]">
              <CardContent className="p-4">
                <div className="relative mb-2 h-4 w-3/4 overflow-hidden rounded bg-[#1a1a2e]">
                  <div className="absolute inset-0 animate-shimmer" />
                </div>
                <div className="relative h-3 w-full overflow-hidden rounded bg-[#1a1a2e]">
                  <div className="absolute inset-0 animate-shimmer" />
                </div>
                <div className="relative mt-1 h-3 w-2/3 overflow-hidden rounded bg-[#1a1a2e]">
                  <div className="absolute inset-0 animate-shimmer" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Error — design tokens, no raw message, recovery action */}
      {!isLoading && error && (
        <div
          className="flex flex-col items-center gap-3 rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-center"
          role="alert"
        >
          <AlertCircle
            className="h-5 w-5 text-destructive"
            aria-hidden="true"
            strokeWidth={1.5}
          />
          <div>
            <p className="text-sm font-medium text-destructive">
              Failed to search knowledge base
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Check your connection and try again
            </p>
          </div>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <RefreshCw className="h-3 w-3" aria-hidden="true" />
              Try again
            </button>
          )}
        </div>
      )}

      {!isLoading && !error && results.length === 0 && (
        <p className="py-8 text-center text-sm text-[#45455a]">
          No results in your knowledge base
        </p>
      )}

      {!isLoading &&
        !error &&
        results.map((r) => (
          <Card
            key={r.chunk_id}
            className="cursor-pointer border-[#2a2a3e] bg-[#14141f] transition-colors hover:border-[#7c5cfc40]"
          >
            <CardHeader className="flex flex-row items-start gap-3 p-4 pb-2">
              <SourceIcon sourceType={r.source_type} />
              <div className="min-w-0 flex-1">
                <h3 className="truncate text-sm font-medium text-[#e2e2e8]">
                  {r.document_title ?? "Untitled"}
                </h3>
                {r.source_path && (
                  <p className="truncate text-xs text-[#45455a]">
                    {r.source_path}
                  </p>
                )}
              </div>
              <span className="shrink-0 text-xs text-[#6b6b80]">
                {Math.round(r.similarity * 100)}%
              </span>
            </CardHeader>
            <CardContent className="px-4 pb-4 pt-0 pl-11">
              <p className="text-sm leading-relaxed text-[#6b6b80]">
                {truncateSnippet(r.content)}
              </p>
            </CardContent>
          </Card>
        ))}
    </div>
  );
}
