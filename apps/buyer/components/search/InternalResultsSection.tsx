"use client";

import { FileText, Code, Globe, File } from "lucide-react";
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
}: {
  results: KbSearchResult[];
  isLoading: boolean;
  error: string | null;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-[#7c5cfc]" />
        <h2 className="text-sm font-medium text-[#e2e2e8]">
          From your knowledge base
        </h2>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card
              key={i}
              className="animate-pulse border-[#2a2a3e] bg-[#14141f]"
            >
              <CardContent className="p-4">
                <div className="mb-2 h-4 w-3/4 rounded bg-[#1a1a2e]" />
                <div className="h-3 w-full rounded bg-[#1a1a2e]" />
                <div className="mt-1 h-3 w-2/3 rounded bg-[#1a1a2e]" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {error && (
        <Card className="border-red-900/50 bg-[#14141f]">
          <CardContent className="p-4 text-sm text-red-400">
            {error}
          </CardContent>
        </Card>
      )}

      {!isLoading && !error && results.length === 0 && (
        <p className="py-8 text-center text-sm text-[#45455a]">
          No internal results
        </p>
      )}

      {!isLoading &&
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
