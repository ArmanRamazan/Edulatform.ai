import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { concepts as conceptsApi } from "@/lib/api";

export function useCourseGraph(token: string | null, courseId: string) {
  return useQuery({
    queryKey: ["concepts", "graph", courseId],
    queryFn: () => conceptsApi.getCourseGraph(token!, courseId),
    enabled: !!token,
  });
}

export function useCourseMastery(token: string | null, courseId: string) {
  return useQuery({
    queryKey: ["concepts", "mastery", courseId],
    queryFn: () => conceptsApi.getCourseMastery(token!, courseId),
    enabled: !!token,
  });
}

export function useCreateConcept(token: string | null, courseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; description?: string; lesson_id?: string; order?: number }) =>
      conceptsApi.create(token!, { course_id: courseId, ...data }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["concepts", "graph", courseId] });
    },
  });
}

export function useDeleteConcept(token: string | null, courseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (conceptId: string) => conceptsApi.delete(token!, conceptId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["concepts", "graph", courseId] });
    },
  });
}
