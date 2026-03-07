"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, FileCode, FileText, Settings } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { useActiveOrg } from "@/hooks/use-active-org";
import { useConceptSources } from "@/hooks/use-concept-hub";

const STORAGE_KEY = "concept-hub-sources-collapsed";

function sourceTypeBadge(sourceType: string | null) {
  const type = (sourceType ?? "doc").toLowerCase();
  if (type.includes("code") || type === "github") {
    return (
      <Badge className="bg-primary/15 text-primary border-primary/30">
        <FileCode className="mr-1 size-3" />
        code
      </Badge>
    );
  }
  if (type.includes("config") || type.includes("yaml") || type.includes("json")) {
    return (
      <Badge className="border-[#fbbf24]/30 bg-[#fbbf24]/10 text-[#fbbf24]">
        <Settings className="mr-1 size-3" />
        config
      </Badge>
    );
  }
  return (
    <Badge className="border-[#38bdf8]/30 bg-[#38bdf8]/10 text-[#38bdf8]">
      <FileText className="mr-1 size-3" />
      doc
    </Badge>
  );
}

interface InternalSourcesBlockProps {
  conceptName: string;
  index: number;
}

export function InternalSourcesBlock({ conceptName, index }: InternalSourcesBlockProps) {
  const { token } = useAuth();
  const { activeOrg } = useActiveOrg();
  const { data: results, isLoading, error } = useConceptSources(
    token,
    activeOrg?.id ?? null,
    conceptName,
  );

  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(STORAGE_KEY) === "true";
  });

  function toggleCollapse() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(STORAGE_KEY, String(next));
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-36" />
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-full" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/30">
        <CardContent className="py-5 text-sm text-destructive">
          Failed to load internal sources
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
    >
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Internal Sources
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={toggleCollapse} className="h-6 w-6 p-0">
            {collapsed ? <ChevronDown className="size-4" /> : <ChevronUp className="size-4" />}
          </Button>
        </CardHeader>
        {!collapsed && (
          <CardContent className="space-y-3">
            {!results || results.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No internal sources found for this concept
              </p>
            ) : (
              results.map((result) => (
                <div
                  key={result.chunk_id}
                  className="rounded-lg border border-border p-3 transition-colors hover:bg-secondary/50"
                >
                  <div className="mb-1.5 flex items-center gap-2">
                    {sourceTypeBadge(result.source_type)}
                    <span className="truncate text-sm font-medium text-card-foreground">
                      {result.document_title ?? "Untitled"}
                    </span>
                  </div>
                  <p className="mb-1.5 line-clamp-2 text-xs text-muted-foreground">
                    {result.content}
                  </p>
                  {result.source_path && (
                    <p className="truncate font-mono text-[10px] text-muted-foreground/60">
                      {result.source_path}
                    </p>
                  )}
                </div>
              ))
            )}
          </CardContent>
        )}
      </Card>
    </motion.div>
  );
}
