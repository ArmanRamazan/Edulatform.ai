import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { pretests as pretestsApi } from "@/lib/api";

export function useStartPretest(token: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (courseId: string) => pretestsApi.start(token!, courseId),
    onSuccess: (_data, courseId) => {
      qc.invalidateQueries({ queryKey: ["pretest", "results", courseId] });
    },
  });
}

export function useAnswerPretest(token: string | null) {
  return useMutation({
    mutationFn: (params: { pretestId: string; answerId: string; answer: string }) =>
      pretestsApi.answer(token!, params.pretestId, {
        answer_id: params.answerId,
        answer: params.answer,
      }),
  });
}

export function usePretestResults(token: string | null, courseId: string) {
  return useQuery({
    queryKey: ["pretest", "results", courseId],
    queryFn: () => pretestsApi.results(token!, courseId),
    enabled: !!token && !!courseId,
    retry: false,
  });
}
