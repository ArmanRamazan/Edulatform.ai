"use client";

import { useEffect, useMemo, useState } from "react";
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

/** Stable confetti positions computed once — avoids layout shift on re-renders. */
const CONFETTI_COLORS = ["#7c5cfc", "#34d399", "#fbbf24", "#38bdf8"];
const CONFETTI_COUNT = 14;

// Deterministic pseudo-random spread using index arithmetic (no Math.random()).
function confettiLeft(i: number) {
  return `${10 + ((i * 73 + 17) % 80)}%`;
}
function confettiDuration(i: number) {
  return `${1.4 + ((i * 37) % 150) / 100}s`;
}
function confettiDelay(i: number) {
  return `${((i * 53) % 50) / 100}s`;
}

export function MissionComplete({ results }: MissionCompleteProps) {
  const isHighScore = results.score > 80;

  // Stable confetti data — computed once, never re-randomised on re-render.
  const confettiItems = useMemo(
    () =>
      Array.from({ length: CONFETTI_COUNT }).map((_, i) => ({
        left: confettiLeft(i),
        color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
        duration: confettiDuration(i),
        delay: confettiDelay(i),
      })),
    [],
  );

  // Score grade label
  const grade = results.score >= 90 ? "Excellent" : results.score >= 70 ? "Good" : "Keep going";

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <Card
        className="relative w-full max-w-lg overflow-hidden border-[#ffffff12] bg-[#14141f]"
        style={{ animation: "mission-complete-in 0.45s cubic-bezier(0.34, 1.38, 0.64, 1) both" }}
      >
        <CardContent className="flex flex-col items-center gap-6 pt-8 text-center">
          {/* Confetti — only rendered for high scores, positions are deterministic */}
          {isHighScore && (
            <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
              {confettiItems.map((item, i) => (
                <div
                  key={i}
                  className="absolute size-2 rounded-full opacity-0"
                  style={{
                    left: item.left,
                    top: "-5%",
                    backgroundColor: item.color,
                    animation: `confetti-fall ${item.duration} ease-in ${item.delay} forwards`,
                  }}
                />
              ))}
            </div>
          )}

          {/* Caption */}
          <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Mission Complete
          </div>

          {/* Score — large mono number with a "/100" context indicator */}
          <div className="flex items-end gap-2">
            <span className="font-mono text-6xl font-bold leading-none text-[#e2e2e8]">
              <CountUp target={results.score} />
            </span>
            <span className="mb-1 font-mono text-xl text-[#6b6b80]">/100</span>
          </div>

          {/* Grade + mastery delta */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-[#6b6b80]">{grade}</span>
            <Badge
              variant="default"
              className="bg-success/15 font-mono text-success"
            >
              +{results.mastery_delta.toFixed(2)} mastery
            </Badge>
          </div>

          {/* Summary */}
          <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">{results.summary}</p>

          {/* Strengths + Gaps — staggered list-item entrance */}
          <div className="grid w-full grid-cols-2 gap-4">
            {results.strengths.length > 0 && (
              <div className="rounded-lg border border-[#ffffff08] bg-[#1a1a2e] p-3 text-left">
                <p className="mb-2 text-xs font-medium uppercase tracking-wider text-success">
                  Strengths
                </p>
                <ul className="space-y-1">
                  {results.strengths.map((s, i) => (
                    <li
                      key={s}
                      className="text-xs text-[#a0a0b0]"
                      style={{
                        animation: `list-item-in 0.25s ease-out ${0.55 + i * 0.07}s both`,
                      }}
                    >
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {results.gaps.length > 0 && (
              <div className="rounded-lg border border-[#ffffff08] bg-[#1a1a2e] p-3 text-left">
                <p className="mb-2 text-xs font-medium uppercase tracking-wider text-warning">
                  Gaps
                </p>
                <ul className="space-y-1">
                  {results.gaps.map((g, i) => (
                    <li
                      key={g}
                      className="text-xs text-[#a0a0b0]"
                      style={{
                        animation: `list-item-in 0.25s ease-out ${0.55 + i * 0.07}s both`,
                      }}
                    >
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
    </div>
  );
}
