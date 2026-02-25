"use client";

import { useState, useCallback } from "react";
import { Header } from "@/components/Header";
import { useAuth } from "@/hooks/use-auth";
import { useDueCards, useReviewCard } from "@/hooks/use-flashcards";

const RATING_BUTTONS = [
  { value: 1, label: "Снова", color: "bg-red-500 hover:bg-red-600" },
  { value: 2, label: "Трудно", color: "bg-orange-500 hover:bg-orange-600" },
  { value: 3, label: "Хорошо", color: "bg-green-500 hover:bg-green-600" },
  { value: 4, label: "Легко", color: "bg-blue-500 hover:bg-blue-600" },
];

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

  const handleFlip = useCallback(() => {
    setFlipped(true);
  }, []);

  const handleRate = useCallback((rating: number) => {
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
  }, [currentCard, reviewStartTime, reviewCard]);

  return (
    <>
      <Header />
      <div className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="mb-6 text-2xl font-bold">Повторение карточек</h1>

        {isLoading ? (
          <p className="text-gray-400">Загрузка...</p>
        ) : !cards.length || currentIndex >= cards.length ? (
          <div className="rounded-lg border border-green-100 bg-green-50 p-8 text-center">
            <p className="text-lg font-medium text-green-700">
              {reviewedCount > 0
                ? `Отлично! Вы повторили ${reviewedCount} карточек.`
                : "Нет карточек для повторения."}
            </p>
            <p className="mt-2 text-sm text-green-600">
              Возвращайтесь позже, когда подойдёт время.
            </p>
          </div>
        ) : (
          <>
            <p className="mb-4 text-sm text-gray-500">
              Карточка {currentIndex + 1} из {cards.length}
              {reviewedCount > 0 && ` (повторено: ${reviewedCount})`}
            </p>

            <div
              onClick={!flipped ? handleFlip : undefined}
              className={`min-h-[200px] rounded-xl border-2 p-8 ${
                flipped
                  ? "border-purple-200 bg-purple-50"
                  : "cursor-pointer border-gray-200 bg-white hover:border-gray-300"
              }`}
            >
              {!flipped ? (
                <div className="flex flex-col items-center justify-center text-center">
                  <p className="text-xs uppercase text-gray-400 mb-3">Вопрос</p>
                  <p className="text-lg font-medium text-gray-800">{currentCard.concept}</p>
                  <p className="mt-4 text-sm text-gray-400">Нажмите, чтобы показать ответ</p>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center text-center">
                  <p className="text-xs uppercase text-gray-400 mb-3">Ответ</p>
                  <p className="text-lg text-gray-800">{currentCard.answer}</p>
                </div>
              )}
            </div>

            {flipped && (
              <div className="mt-4 flex justify-center gap-3">
                {RATING_BUTTONS.map((btn) => (
                  <button
                    key={btn.value}
                    onClick={() => handleRate(btn.value)}
                    disabled={reviewCard.isPending}
                    className={`rounded-lg px-4 py-2 text-sm font-medium text-white ${btn.color} disabled:opacity-50`}
                  >
                    {btn.label}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
