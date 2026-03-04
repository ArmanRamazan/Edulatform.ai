"use client";

import { useAuth } from "@/hooks/use-auth";
import { useMyRecommendations } from "@/hooks/use-recommendations";
import { CourseCard } from "@/components/CourseCard";
import { CourseCardSkeleton } from "@/components/CourseCardSkeleton";

export function PersonalizedRecommendations() {
  const { token } = useAuth();
  const { data: recommended, isLoading } = useMyRecommendations(token);

  if (!token) {
    return null;
  }

  if (isLoading) {
    return (
      <section className="mx-auto max-w-6xl px-4 py-10">
        <h2 className="mb-6 text-2xl font-bold text-gray-900">
          Рекомендовано для вас
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <CourseCardSkeleton key={i} />
          ))}
        </div>
      </section>
    );
  }

  if (!recommended || recommended.length === 0) {
    return null;
  }

  return (
    <section className="mx-auto max-w-6xl px-4 py-10">
      <h2 className="mb-6 text-2xl font-bold text-gray-900">
        Рекомендовано для вас
      </h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {recommended.map((course) => (
          <CourseCard key={course.id} course={course} />
        ))}
      </div>
    </section>
  );
}
