"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BookOpen, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { useDueCards, useReviewCard } from "@/hooks/use-flashcards";

// Rating config — theme-token colors, keyboard digit shortcuts (1/2/3/4)
const RATING_BUTTONS = [
  {
    value: 1,
    label: "Снова",
    key: "1",
    className:
      "bg-destructive/15 text-destructive ring-1 ring-destructive/30 hover:bg-destructive/25 active:scale-95",
  },
  {
    value: 2,
    label: "Трудно",
    key: "2",
    className:
      "bg-warning/15 text-warning ring-1 ring-warning/30 hover:bg-warning/25 active:scale-95",
  },
  {
    value: 3,
    label: "Хорошо",
    key: "3",
    className:
      "bg-success/15 text-success ring-1 ring-success/30 hover:bg-success/25 active:scale-95",
  },
  {
    value: 4,
    label: "Легко",
    key: "4",
    className:
      "bg-info/15 text-info ring-1 ring-info/30 hover:bg-info/25 active:scale-95",
  },
] as const;

// ── Skeleton ────────────────────────────────────────────────────────────────
function FlashcardSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading flashcards">
      {/* Counter */}
      <div className="relative h-4 w-36 overflow-hidden rounded bg-card border border-border">
        <div className="absolute inset-0 animate-shimmer" />
      </div>
      {/* Card */}
      <div className="relative min-h-[220px] overflow-hidden rounded-2xl border border-border bg-card">
        <div className="absolute inset-0 animate-shimmer" />
      </div>
      {/* Rating row */}
      <div className="flex justify-center gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="relative h-10 w-20 overflow-hidden rounded-lg bg-card border border-border"
          >
            <div className="absolute inset-0 animate-shimmer" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function FlashcardsPage() {
  const { token } = useAuth();
  const { data, isLoading } = useDueCards(token);
  const reviewCard = useReviewCard(token);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [reviewStartTime, setReviewStartTime] = useState<number>(Date.now());
  const [reviewedCount, setReviewedCount] = useState(0);

  const cards = data?.items ?? [];
  const currentCard = cards[currentIndex];
  const isDone = !isLoading && (!cards.length || currentIndex >= cards.length);

  const handleFlip = useCallback(() => {
    setFlipped(true);
  }, []);

  const handleRate = useCallback(
    (rating: number) => {
      if (!currentCard) return;
      const durationMs = Date.now() - reviewStartTime;
      reviewCard.mutate(
        { cardId: currentCard.id, rating, durationMs },
        {
          onSuccess: () => {
            setFlipped(false);
            setReviewedCount((c) => c + 1);
            setCurrentIndex((i) => i + 1);
            setReviewStartTime(Date.now());
          },
        },
      );
    },
    [currentCard, reviewStartTime, reviewCard],
  );

  // ── Keyboard shortcuts ────────────────────────────────────────────────────
  // Space → flip card
  // 1/2/3/4 → rate when flipped
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === " " && !flipped) {
        e.preventDefault();
        handleFlip();
      }
      if (flipped && !reviewCard.isPending) {
        const btn = RATING_BUTTONS.find((b) => b.key === e.key);
        if (btn) handleRate(btn.value);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [flipped, handleFlip, handleRate, reviewCard.isPending]);

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Повторение карточек</h1>
        {!isDone && !isLoading && (
          <span className="text-sm text-muted-foreground">
            Space — показать ответ · 1-4 — оценить
          </span>
        )}
      </div>

      {/* ── Loading ── */}
      {isLoading && <FlashcardSkeleton />}

      {/* ── Done / Empty ── */}
      {isDone && (
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="flex flex-col items-center gap-4 rounded-2xl border border-border bg-card p-10 text-center"
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-success/15">
            <CheckCircle2 className="h-7 w-7 text-success" aria-hidden="true" />
          </div>
          <div>
            <p className="text-lg font-semibold text-foreground">
              {reviewedCount > 0
                ? `Отлично! Повторено ${reviewedCount} карточек`
                : "Нет карточек для повторения"}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Возвращайтесь позже, когда подойдёт время.
            </p>
          </div>
          <Link
            href="/dashboard"
            className="mt-2 rounded-xl bg-primary/10 px-5 py-2 text-sm font-semibold text-primary ring-1 ring-primary/20 transition-all hover:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            На главную
          </Link>
        </motion.div>
      )}

      {/* ── Active review ── */}
      {!isLoading && !isDone && currentCard && (
        <>
          {/* Progress counter */}
          <div className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
            <BookOpen className="h-4 w-4" aria-hidden="true" />
            <span>
              Карточка{" "}
              <span className="tabular-nums font-semibold text-foreground">
                {currentIndex + 1}
              </span>{" "}
              из{" "}
              <span className="tabular-nums font-semibold text-foreground">{cards.length}</span>
            </span>
            {reviewedCount > 0 && (
              <span className="ml-1 text-muted-foreground/60">
                · повторено: {reviewedCount}
              </span>
            )}
          </div>

          {/* Progress bar */}
          <div className="mb-4 h-1 overflow-hidden rounded-full bg-secondary">
            <motion.div
              className="h-full rounded-full bg-primary"
              initial={false}
              animate={{ width: `${((currentIndex + 1) / cards.length) * 100}%` }}
              transition={{ duration: 0.4, ease: "easeOut" }}
            />
          </div>

          {/* Flashcard */}
          <AnimatePresence mode="wait">
            <motion.div
              key={`${currentIndex}-${flipped ? "back" : "front"}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              <div
                onClick={!flipped ? handleFlip : undefined}
                onKeyDown={
                  !flipped
                    ? (e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          handleFlip();
                        }
                      }
                    : undefined
                }
                role={!flipped ? "button" : undefined}
                tabIndex={!flipped ? 0 : undefined}
                aria-label={!flipped ? "Показать ответ" : undefined}
                className={[
                  "min-h-[220px] rounded-2xl border-2 p-8 transition-all duration-200",
                  flipped
                    ? "border-primary/30 bg-primary/5"
                    : "cursor-pointer border-border bg-card hover:border-primary/40 hover:bg-card/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.99]",
                ].join(" ")}
              >
                {!flipped ? (
                  <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
                    <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground/60">
                      Вопрос
                    </p>
                    <p className="text-lg font-semibold text-foreground">{currentCard.concept}</p>
                    <p className="mt-2 text-xs text-muted-foreground/50">
                      Нажмите или Space, чтобы показать ответ
                    </p>
                  </div>
                ) : (
                  <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
                    <p className="text-xs font-medium uppercase tracking-widest text-primary/60">
                      Ответ
                    </p>
                    <p className="text-lg text-foreground">{currentCard.answer}</p>
                  </div>
                )}
              </div>
            </motion.div>
          </AnimatePresence>

          {/* Rating buttons */}
          <AnimatePresence>
            {flipped && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 4 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className="mt-4 flex justify-center gap-3"
              >
                {RATING_BUTTONS.map((btn) => (
                  <button
                    key={btn.value}
                    onClick={() => handleRate(btn.value)}
                    disabled={reviewCard.isPending}
                    aria-label={`Оценить: ${btn.label} (клавиша ${btn.key})`}
                    className={[
                      "flex flex-col items-center gap-1 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
                      btn.className,
                    ].join(" ")}
                  >
                    <span>{btn.label}</span>
                    <span className="rounded border border-current/20 px-1 text-[10px] font-mono opacity-60">
                      {btn.key}
                    </span>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </div>
  );
}
