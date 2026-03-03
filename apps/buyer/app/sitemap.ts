import type { MetadataRoute } from "next";

const BASE_URL =
  process.env.NEXT_PUBLIC_BASE_URL || "https://eduplatform.ru";
const COURSE_SERVICE_URL =
  process.env.COURSE_SERVICE_URL || "http://localhost:8002";

interface CourseItem {
  id: string;
  created_at: string;
}

interface CourseListResponse {
  items: CourseItem[];
  total: number;
}

async function fetchAllCourses(): Promise<CourseItem[]> {
  const courses: CourseItem[] = [];
  const perPage = 100;
  let offset = 0;

  try {
    const first = await fetch(
      `${COURSE_SERVICE_URL}/courses?limit=${perPage}&offset=0`,
      { next: { revalidate: 3600 } },
    );
    if (!first.ok) return [];
    const firstPage: CourseListResponse = await first.json();
    courses.push(...firstPage.items);
    const total = Math.min(firstPage.total, 50000 - 5);

    while (courses.length < total) {
      offset += perPage;
      const res = await fetch(
        `${COURSE_SERVICE_URL}/courses?limit=${perPage}&offset=${offset}`,
        { next: { revalidate: 3600 } },
      );
      if (!res.ok) break;
      const page: CourseListResponse = await res.json();
      if (page.items.length === 0) break;
      courses.push(...page.items);
    }
  } catch {
    return courses;
  }

  return courses;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticEntries: MetadataRoute.Sitemap = [
    { url: BASE_URL, changeFrequency: "weekly", priority: 1.0 },
    { url: `${BASE_URL}/courses`, changeFrequency: "daily", priority: 0.9 },
    { url: `${BASE_URL}/pricing`, changeFrequency: "monthly", priority: 0.7 },
    { url: `${BASE_URL}/login`, changeFrequency: "yearly", priority: 0.3 },
    { url: `${BASE_URL}/register`, changeFrequency: "yearly", priority: 0.3 },
  ];

  const courses = await fetchAllCourses();

  const courseEntries: MetadataRoute.Sitemap = courses.map((course) => ({
    url: `${BASE_URL}/courses/${course.id}`,
    lastModified: course.created_at,
    changeFrequency: "weekly" as const,
    priority: 0.8,
  }));

  return [...staticEntries, ...courseEntries];
}
