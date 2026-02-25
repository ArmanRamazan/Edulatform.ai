import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { quizzes as quizzesApi } from "@/lib/api";

export function useQuiz(token: string | null, lessonId: string) {
  return useQuery({
    queryKey: ["quiz", lessonId],
    queryFn: () => quizzesApi.getByLesson(token!, lessonId),
    enabled: !!token,
    retry: false,
  });
}

export function useSubmitQuiz(token: string | null, quizId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (answers: number[]) => quizzesApi.submit(token!, quizId, answers),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quizAttempts", quizId] });
    },
  });
}

export function useMyAttempts(token: string | null, quizId: string | undefined) {
  return useQuery({
    queryKey: ["quizAttempts", quizId],
    queryFn: () => quizzesApi.myAttempts(token!, quizId!),
    enabled: !!token && !!quizId,
  });
}
