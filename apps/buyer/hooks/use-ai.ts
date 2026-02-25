import { useMutation, useQuery } from "@tanstack/react-query";
import { ai as aiApi } from "@/lib/api";

export function useGenerateQuiz(token: string | null) {
  return useMutation({
    mutationFn: ({ lessonId, content }: { lessonId: string; content: string }) =>
      aiApi.generateQuiz(token!, lessonId, content),
  });
}

export function useSummary(token: string | null, lessonId: string, content: string) {
  return useQuery({
    queryKey: ["summary", lessonId],
    queryFn: () => aiApi.generateSummary(token!, lessonId, content),
    enabled: !!token && content.length > 10,
    staleTime: 5 * 60 * 1000,
  });
}
