"use client";

import dynamic from "next/dynamic";
import { BarChart3 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { TeamOverview } from "@/components/admin/analytics/TeamOverview";
import { BottleneckReport } from "@/components/admin/analytics/BottleneckReport";

// Dynamic import for the heavy heatmap component
const ConceptCoverage = dynamic(
  () =>
    import("@/components/admin/analytics/ConceptCoverage").then(
      (mod) => mod.ConceptCoverage,
    ),
  {
    ssr: false,
    loading: () => (
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-48" />
        </CardHeader>
        <CardContent className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex items-center gap-2">
              <Skeleton className="h-4 w-32" />
              <div className="flex gap-1">
                {Array.from({ length: 8 }).map((_, j) => (
                  <Skeleton key={j} className="h-7 w-7 rounded-sm" />
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    ),
  },
);

export default function AnalyticsPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-8 print:space-y-4 print:bg-white print:text-black">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <BarChart3 className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-foreground">Team Analytics</h1>
          <p className="text-sm text-muted-foreground">
            Track your team&apos;s knowledge progress and identify gaps
          </p>
        </div>
      </div>

      {/* Team overview with summary cards + distribution chart */}
      <section>
        <TeamOverview />
      </section>

      {/* Concept coverage heatmap */}
      <section>
        <ConceptCoverage />
      </section>

      {/* Bottleneck report */}
      <section>
        <BottleneckReport />
      </section>

      {/* Print styles */}
      <style jsx global>{`
        @media print {
          .bg-sidebar,
          aside,
          nav,
          button[aria-label="Open navigation"] {
            display: none !important;
          }
          main {
            padding: 0 !important;
            overflow: visible !important;
          }
          .print\\:bg-white {
            background: white !important;
          }
          .print\\:text-black {
            color: black !important;
          }
        }
      `}</style>
    </div>
  );
}
