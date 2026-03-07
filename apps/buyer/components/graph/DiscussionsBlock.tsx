"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, MessageSquare } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const STORAGE_KEY = "concept-hub-discussions-collapsed";

interface DiscussionsBlockProps {
  conceptId: string;
  conceptName: string;
  index: number;
}

export function DiscussionsBlock({ conceptId: _conceptId, conceptName, index }: DiscussionsBlockProps) {
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(STORAGE_KEY) === "true";
  });

  function toggleCollapse() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(STORAGE_KEY, String(next));
  }

  // Discussions API does not support concept-based filtering yet.
  // This block will be connected once GET /discussions?concept_id=X is available.

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
    >
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Discussions
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleCollapse}
            className="h-6 w-6 p-0"
            aria-label={collapsed ? "Expand Discussions" : "Collapse Discussions"}
            aria-expanded={!collapsed}
          >
            {collapsed ? <ChevronDown className="size-4" /> : <ChevronUp className="size-4" />}
          </Button>
        </CardHeader>
        {!collapsed && (
          <CardContent>
            <div className="flex flex-col items-center justify-center py-6 text-center">
              <MessageSquare className="mb-3 size-12 text-muted-foreground/40" aria-hidden="true" />
              <p className="mb-1 text-sm font-medium text-card-foreground">
                Discussions for &quot;{conceptName}&quot;
              </p>
              <p className="text-xs text-muted-foreground">
                Concept-level discussions are coming soon
              </p>
            </div>
          </CardContent>
        )}
      </Card>
    </motion.div>
  );
}
