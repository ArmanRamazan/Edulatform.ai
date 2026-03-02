"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { courses, type CourseCreate, type CourseUpdate } from "@/lib/api";

export function useTeacherCourses(token: string | null) {
  return useQuery({
    queryKey: ["teacher-courses"],
    queryFn: () => courses.my(token!),
    enabled: !!token,
  });
}

export function useCurriculum(token: string | null, courseId: string) {
  return useQuery({
    queryKey: ["curriculum", courseId],
    queryFn: () => courses.curriculum(token!, courseId),
    enabled: !!token && !!courseId,
  });
}

export function useCreateCourse(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CourseCreate) => courses.create(token!, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teacher-courses"] });
    },
  });
}

export function useUpdateCourse(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: CourseUpdate }) =>
      courses.update(token!, id, body),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["teacher-courses"] });
      queryClient.invalidateQueries({ queryKey: ["curriculum", variables.id] });
    },
  });
}
