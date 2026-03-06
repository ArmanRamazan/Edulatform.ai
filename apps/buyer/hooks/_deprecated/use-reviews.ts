import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { reviews as reviewsApi, type Review } from "@/lib/api";

export function useCourseReviews(courseId: string, params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ["reviews", courseId, params],
    queryFn: () => reviewsApi.byCourse(courseId, params),
  });
}

export function useCreateReview(token: string | null, courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { course_id: string; rating: number; comment?: string }) =>
      reviewsApi.create(token!, data),
    onMutate: async (newReview) => {
      await queryClient.cancelQueries({ queryKey: ["reviews", courseId] });
      const previous = queryClient.getQueryData(["reviews", courseId, undefined]);
      queryClient.setQueryData(
        ["reviews", courseId, undefined],
        (old: { items: Review[]; total: number } | undefined) =>
          old
            ? {
                items: [
                  { id: "optimistic", student_id: "", course_id: courseId, rating: newReview.rating, comment: newReview.comment || "", created_at: new Date().toISOString() } as Review,
                  ...old.items,
                ],
                total: old.total + 1,
              }
            : undefined,
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["reviews", courseId, undefined], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews", courseId] });
    },
  });
}
