"use client";

import { useId } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ConceptData } from "@/lib/api";

interface ConceptHeaderProps {
  concept: ConceptData;
  allConcepts: ConceptData[];
  mastery: number;
  index: number;
}

function MasteryRing({ mastery }: { mastery: number }) {
  // useId ensures each instance gets a unique gradient ID — otherwise all SVGs
  // on the page share the same <defs> and only the last gradient wins.
  const uid = useId();
  const gradientId = `mastery-gradient-${uid.replace(/:/g, "")}`;

  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (mastery / 100) * circumference;

  return (
    <svg width="128" height="128" viewBox="0 0 128 128" aria-hidden="true">
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#7c5cfc" />
          <stop offset="100%" stopColor="#9b80fd" />
        </linearGradient>
      </defs>
      <circle
        cx="64"
        cy="64"
        r={radius}
        fill="none"
        stroke="#22223a"
        strokeWidth="8"
      />
      <circle
        cx="64"
        cy="64"
        r={radius}
        fill="none"
        stroke={`url(#${gradientId})`}
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform="rotate(-90 64 64)"
        className="transition-all duration-700"
      />
      <text
        x="64"
        y="62"
        textAnchor="middle"
        fill="#e2e2e8"
        fontSize="22"
        fontWeight="600"
        fontFamily="var(--font-mono, ui-monospace, monospace)"
        letterSpacing="-0.02em"
      >
        {mastery}%
      </text>
      <text
        x="64"
        y="80"
        textAnchor="middle"
        fill="#6b6b80"
        fontSize="10"
        fontWeight="400"
        letterSpacing="0.06em"
        fontFamily="var(--font-sans, ui-sans-serif, system-ui)"
      >
        MASTERY
      </text>
    </svg>
  );
}

export function ConceptHeader({
  concept,
  allConcepts,
  mastery,
  index,
}: ConceptHeaderProps) {
  const prerequisites = allConcepts.filter((c) =>
    concept.prerequisites.includes(c.id),
  );

  const dependents = allConcepts.filter((c) =>
    c.prerequisites.includes(concept.id),
  );

  const parentConcept = concept.parent_id
    ? allConcepts.find((c) => c.id === concept.parent_id)
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
    >
      <Card>
        <CardContent className="py-6">
          {/* Breadcrumb */}
          <nav aria-label="Breadcrumb" className="mb-4 flex items-center gap-1.5 text-xs text-muted-foreground">
            <Link
              href="/graph"
              className="transition-colors duration-150 hover:text-foreground"
            >
              Graph
            </Link>
            {parentConcept && (
              <>
                <ChevronRight className="size-3 opacity-50" />
                <Link
                  href={`/graph/${parentConcept.id}`}
                  className="transition-colors duration-150 hover:text-foreground"
                >
                  {parentConcept.name}
                </Link>
              </>
            )}
            <ChevronRight className="size-3 opacity-50" />
            <span aria-current="page" className="font-medium text-foreground">
              {concept.name}
            </span>
          </nav>

          <div className="flex items-start gap-6">
            <div className="shrink-0" role="img" aria-label={`${mastery}% mastery`}>
              <MasteryRing mastery={mastery} />
            </div>

            <div className="flex-1 min-w-0">
              <h1 className="mb-2 text-2xl font-semibold tracking-tight text-card-foreground">
                {concept.name}
              </h1>
              {concept.description && (
                <p className="mb-4 text-sm text-muted-foreground leading-relaxed">
                  {concept.description}
                </p>
              )}

              {/* Prerequisites */}
              {prerequisites.length > 0 && (
                <div className="mb-3">
                  <span className="mr-2 text-xs text-muted-foreground">
                    Requires:
                  </span>
                  <div className="inline-flex flex-wrap gap-1.5">
                    {prerequisites.map((p) => (
                      <Link key={p.id} href={`/graph/${p.id}`}>
                        <Badge
                          variant="outline"
                          className="cursor-pointer transition-colors hover:border-primary/40 hover:bg-primary/10 hover:text-primary"
                        >
                          {p.name}
                        </Badge>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Dependents */}
              {dependents.length > 0 && (
                <div>
                  <span className="mr-2 text-xs text-muted-foreground">
                    Unlocks:
                  </span>
                  <div className="inline-flex flex-wrap gap-1.5">
                    {dependents.map((d) => (
                      <Link key={d.id} href={`/graph/${d.id}`}>
                        <Badge
                          variant="secondary"
                          className="cursor-pointer transition-colors hover:bg-success/10 hover:text-success"
                        >
                          {d.name}
                        </Badge>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
