"use client";

import Image from "next/image";
import { ExternalLink, BookmarkPlus } from "lucide-react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import type { ExternalSearchResult } from "@/lib/api";

function DomainFavicon({ domain }: { domain: string }) {
  return (
    <Image
      src={`https://www.google.com/s2/favicons?sz=16&domain=${encodeURIComponent(domain)}`}
      alt=""
      width={16}
      height={16}
      className="h-4 w-4 shrink-0 rounded"
      unoptimized
    />
  );
}

export function ExternalResultsSection({
  results,
  isLoading,
  error,
}: {
  results: ExternalSearchResult[];
  isLoading: boolean;
  error: string | null;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-[#38bdf8]" />
        <h2 className="text-sm font-medium text-[#e2e2e8]">From the web</h2>
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
                <div className="mt-1 h-3 w-1/2 rounded bg-[#1a1a2e]" />
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
          No external results
        </p>
      )}

      {!isLoading &&
        results.map((r) => (
          <a
            key={r.url}
            href={r.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block"
          >
            <Card className="cursor-pointer border-[#2a2a3e] bg-[#14141f] transition-colors hover:border-[#38bdf840]">
              <CardHeader className="flex flex-row items-start gap-3 p-4 pb-2">
                <DomainFavicon domain={r.domain} />
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-sm font-medium text-[#e2e2e8]">
                    {r.title}
                  </h3>
                  <p className="flex items-center gap-1 text-xs text-[#45455a]">
                    {r.domain}
                    <ExternalLink className="h-3 w-3" />
                  </p>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    // Placeholder: Save to KB
                  }}
                  className="shrink-0 rounded-md p-1 text-[#6b6b80] transition-colors hover:bg-[#1a1a2e] hover:text-[#38bdf8]"
                  title="Save to knowledge base"
                >
                  <BookmarkPlus className="h-4 w-4" />
                </button>
              </CardHeader>
              <CardContent className="px-4 pb-4 pt-0 pl-11">
                <p className="text-sm leading-relaxed text-[#6b6b80]">
                  {r.snippet}
                </p>
              </CardContent>
            </Card>
          </a>
        ))}
    </div>
  );
}
