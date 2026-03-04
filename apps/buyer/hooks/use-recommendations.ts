import { useQuery } from "@tanstack/react-query";
import { recommendations, courses, type Course } from "@/lib/api";

export function useSimilarCourses(courseId: string) {
  return useQuery({
    queryKey: ["recommendations", "similar", courseId],
    queryFn: async (): Promise<Course[]> => {
      const recs = await recommendations.forCourse(courseId);
      if (recs.length === 0) return [];
      const top = recs.slice(0, 5);
      const results = await Promise.allSettled(
        top.map((r) => courses.get(r.course_id)),
      );
      return results
        .filter(
          (r): r is PromiseFulfilledResult<Course> => r.status === "fulfilled",
        )
        .map((r) => r.value);
    },
  });
}

export function useMyRecommendations(token: string | null) {
  return useQuery({
    queryKey: ["recommendations", "me"],
    queryFn: async (): Promise<Course[]> => {
      if (!token) return [];
      const recs = await recommendations.forMe(token);
      if (recs.length === 0) return [];
      const top = recs.slice(0, 6);
      const results = await Promise.allSettled(
        top.map((r) => courses.get(r.course_id)),
      );
      return results
        .filter(
          (r): r is PromiseFulfilledResult<Course> => r.status === "fulfilled",
        )
        .map((r) => r.value);
    },
    enabled: !!token,
  });
}
