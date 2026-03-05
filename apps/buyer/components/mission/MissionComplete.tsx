"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import type { CoachEndResponse } from "@/lib/api";

interface MissionCompleteProps {
  results: CoachEndResponse;
}

function CountUp({ target, duration = 1200 }: { target: number; duration?: number }) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    const start = performance.now();
    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(target * eased));
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }, [target, duration]);

  return <>{value}</>;
}

export function MissionComplete({ results }: MissionCompleteProps) {
  const isHighScore = results.score > 80;

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <Card className="w-full max-w-lg">
        <CardContent className="flex flex-col items-center gap-6 pt-8 text-center">
          {isHighScore && (
            <div className="pointer-events-none absolute inset-0 overflow-hidden">
              {Array.from({ length: 12 }).map((_, i) => (
                <div
                  key={i}
                  className="absolute size-2 rounded-full opacity-0"
                  style={{
                    left: `${10 + Math.random() * 80}%`,
                    top: `-5%`,
                    backgroundColor: ["#7c5cfc", "#34d399", "#fbbf24", "#38bdf8"][i % 4],
                    animation: `confetti-fall ${1.5 + Math.random() * 1.5}s ease-in ${Math.random() * 0.5}s forwards`,
                  }}
                />
              ))}
            </div>
          )}

          <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Mission Complete
          </div>

          <div className="font-mono text-6xl font-bold text-card-foreground">
            <CountUp target={results.score} />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Mastery</span>
            <Badge variant="default" className="bg-emerald-500/20 text-emerald-400">
              +{results.mastery_delta.toFixed(2)}
            </Badge>
          </div>

          <p className="text-sm text-muted-foreground">{results.summary}</p>

          <div className="grid w-full grid-cols-2 gap-4">
            {results.strengths.length > 0 && (
              <div className="rounded-lg bg-secondary p-3 text-left">
                <p className="mb-2 text-xs font-medium uppercase tracking-wider text-emerald-400">
                  Strengths
                </p>
                <ul className="space-y-1">
                  {results.strengths.map((s) => (
                    <li key={s} className="text-xs text-muted-foreground">
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {results.gaps.length > 0 && (
              <div className="rounded-lg bg-secondary p-3 text-left">
                <p className="mb-2 text-xs font-medium uppercase tracking-wider text-amber-400">
                  Gaps
                </p>
                <ul className="space-y-1">
                  {results.gaps.map((g) => (
                    <li key={g} className="text-xs text-muted-foreground">
                      {g}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <Button asChild className="w-full">
            <Link href="/dashboard">Back to Dashboard</Link>
          </Button>
        </CardContent>
      </Card>

      <style jsx>{`
        @keyframes confetti-fall {
          0% {
            opacity: 1;
            transform: translateY(0) rotate(0deg);
          }
          100% {
            opacity: 0;
            transform: translateY(400px) rotate(720deg);
          }
        }
      `}</style>
    </div>
  );
}
