import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { flashcards as flashcardsApi } from "@/lib/api";

export function useDueCards(token: string | null) {
  return useQuery({
    queryKey: ["flashcards", "due"],
    queryFn: () => flashcardsApi.due(token!),
    enabled: !!token,
    refetchInterval: 60000,
  });
}

export function useDueCount(token: string | null) {
  return useQuery({
    queryKey: ["flashcards", "due"],
    queryFn: () => flashcardsApi.due(token!, { limit: 1 }),
    enabled: !!token,
    select: (data) => data.total,
    refetchInterval: 60000,
  });
}

export function useReviewCard(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ cardId, rating, durationMs }: { cardId: string; rating: number; durationMs?: number }) =>
      flashcardsApi.review(token!, cardId, { rating, review_duration_ms: durationMs }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["flashcards"] });
    },
  });
}

export function useCreateFlashcard(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { course_id: string; concept: string; answer: string; source_type?: string }) =>
      flashcardsApi.create(token!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["flashcards"] });
    },
  });
}
