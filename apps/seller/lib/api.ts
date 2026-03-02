const IDENTITY_URL = "/api/identity";
const COURSE_URL = "/api/course";
const PAYMENT_URL = "/api/payment";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: "student" | "teacher" | "admin";
  is_verified: boolean;
  email_verified: boolean;
  created_at: string;
}

export interface Course {
  id: string;
  teacher_id: string;
  title: string;
  description: string;
  is_free: boolean;
  price: number | null;
  duration_minutes: number;
  level: "beginner" | "intermediate" | "advanced";
  created_at: string;
  avg_rating: number | null;
  review_count: number;
  category_id: string | null;
}

export interface CourseList {
  items: Course[];
  total: number;
}

export interface CourseCreate {
  title: string;
  description: string;
  is_free: boolean;
  price: number | null;
  duration_minutes: number;
  level: "beginner" | "intermediate" | "advanced";
  category_id: string | null;
}

export interface CourseUpdate {
  title?: string;
  description?: string;
  is_free?: boolean;
  price?: number | null;
  duration_minutes?: number;
  level?: "beginner" | "intermediate" | "advanced";
  category_id?: string | null;
}

export interface Module {
  id: string;
  course_id: string;
  title: string;
  order: number;
  created_at: string;
}

export interface Lesson {
  id: string;
  module_id: string;
  title: string;
  content: string;
  video_url: string | null;
  duration_minutes: number;
  order: number;
  created_at: string;
}

export interface CurriculumModule {
  id: string;
  course_id: string;
  title: string;
  order: number;
  created_at: string;
  lessons: Lesson[];
}

export interface CurriculumResponse {
  course: Course;
  modules: CurriculumModule[];
  total_lessons: number;
}

export interface CourseAnalytics {
  course_id: string;
  title: string;
  avg_rating: number | null;
  review_count: number;
  module_count: number;
  lesson_count: number;
}

export interface TeacherAnalyticsSummary {
  total_courses: number;
  total_lessons: number;
  avg_rating: number | null;
  total_reviews: number;
  courses: CourseAnalytics[];
}

export interface EarningResponse {
  id: string;
  teacher_id: string;
  course_id: string;
  payment_id: string;
  gross_amount: string;
  commission_rate: string;
  net_amount: string;
  status: string;
  created_at: string;
}

export interface EarningsSummary {
  total_gross: string;
  total_net: string;
  total_pending: string;
  total_paid: string;
  earnings: EarningResponse[];
}

export interface EarningListResponse {
  items: EarningResponse[];
  total: number;
}

export interface PayoutResponse {
  id: string;
  teacher_id: string;
  amount: string;
  stripe_transfer_id: string | null;
  status: string;
  requested_at: string;
  completed_at: string | null;
}

export interface PayoutListResponse {
  items: PayoutResponse[];
  total: number;
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

export const identity = {
  login(email: string, password: string) {
    return request<TokenResponse>(`${IDENTITY_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  },

  me(token: string) {
    return request<User>(`${IDENTITY_URL}/users/me`, {
      headers: authHeaders(token),
    });
  },
};

export const courses = {
  list(token: string, params?: Record<string, string | undefined>) {
    const qs = new URLSearchParams();
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined) qs.set(k, v);
      }
    }
    const query = qs.toString();
    return request<CourseList>(`${COURSE_URL}/courses${query ? `?${query}` : ""}`, {
      headers: authHeaders(token),
    });
  },

  get(token: string, id: string) {
    return request<Course>(`${COURSE_URL}/courses/${id}`, {
      headers: authHeaders(token),
    });
  },

  create(token: string, body: CourseCreate) {
    return request<Course>(`${COURSE_URL}/courses`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(body),
    });
  },

  update(token: string, id: string, body: CourseUpdate) {
    return request<Course>(`${COURSE_URL}/courses/${id}`, {
      method: "PATCH",
      headers: authHeaders(token),
      body: JSON.stringify(body),
    });
  },

  curriculum(token: string, id: string) {
    return request<CurriculumResponse>(`${COURSE_URL}/courses/${id}/curriculum`, {
      headers: authHeaders(token),
    });
  },
};

export const analytics = {
  getSummary(token: string) {
    return request<TeacherAnalyticsSummary>(`${COURSE_URL}/analytics/teacher`, {
      headers: authHeaders(token),
    });
  },
};

export const earnings = {
  getSummary(token: string) {
    return request<EarningsSummary>(`${PAYMENT_URL}/earnings/me/summary`, {
      headers: authHeaders(token),
    });
  },

  listEarnings(token: string, limit = 20, offset = 0) {
    return request<EarningListResponse>(
      `${PAYMENT_URL}/earnings/me?limit=${limit}&offset=${offset}`,
      { headers: authHeaders(token) },
    );
  },

  requestPayout(token: string, amount: number) {
    return request<PayoutResponse>(`${PAYMENT_URL}/earnings/payouts`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ amount }),
    });
  },

  listPayouts(token: string, limit = 20, offset = 0) {
    return request<PayoutListResponse>(
      `${PAYMENT_URL}/earnings/payouts?limit=${limit}&offset=${offset}`,
      { headers: authHeaders(token) },
    );
  },
};
