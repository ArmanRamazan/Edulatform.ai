"use client";

import { useSimilarCourses } from "@/hooks/use-recommendations";
import { CourseCard } from "@/components/CourseCard";
import { CourseCardSkeleton } from "@/components/CourseCardSkeleton";

interface SimilarCoursesProps {
  courseId: string;
}

export function SimilarCourses({ courseId }: SimilarCoursesProps) {
  const { data: similarCourses, isLoading } = useSimilarCourses(courseId);

  if (isLoading) {
    return (
      <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-bold">Похожие курсы</h2>
        <div className="flex gap-4 overflow-x-auto pb-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="w-72 flex-shrink-0">
              <CourseCardSkeleton />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!similarCourses || similarCourses.length === 0) {
    return null;
  }

  return (
    <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
      <h2 className="mb-4 text-lg font-bold">Похожие курсы</h2>
      <div className="flex gap-4 overflow-x-auto pb-2">
        {similarCourses.map((course) => (
          <div key={course.id} className="w-72 flex-shrink-0">
            <CourseCard course={course} />
          </div>
        ))}
      </div>
    </div>
  );
}
