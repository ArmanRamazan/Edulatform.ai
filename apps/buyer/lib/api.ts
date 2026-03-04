const IDENTITY_URL = "/api/identity";
const COURSE_URL = "/api/course";
const ENROLLMENT_URL = "/api/enrollment";
const PAYMENT_URL = "/api/payment";
const NOTIFICATION_URL = "/api/notification";
const AI_URL = "/api/ai";
const LEARNING_URL = "/api/learning";

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

export interface Category {
  id: string;
  name: string;
  slug: string;
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

export interface Review {
  id: string;
  student_id: string;
  course_id: string;
  rating: number;
  comment: string;
  created_at: string;
}

export interface ReviewList {
  items: Review[];
  total: number;
}

export interface CourseProgress {
  course_id: string;
  completed_lessons: number;
  total_lessons: number;
  percentage: number;
}

export interface Enrollment {
  id: string;
  student_id: string;
  course_id: string;
  payment_id: string | null;
  status: "enrolled" | "in_progress" | "completed";
  enrolled_at: string;
}

export interface EnrollmentList {
  items: Enrollment[];
  total: number;
}

export interface Payment {
  id: string;
  student_id: string;
  course_id: string;
  amount: string;
  status: "pending" | "completed" | "failed" | "refunded";
  created_at: string;
}

export interface PaymentList {
  items: Payment[];
  total: number;
}

export interface Notification {
  id: string;
  user_id: string;
  type: "registration" | "enrollment" | "payment";
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
}

export interface NotificationList {
  items: Notification[];
  total: number;
}

export interface QuizQuestion {
  id: string;
  text: string;
  options: string[];
  order: number;
}

export interface QuizData {
  id: string;
  lesson_id: string;
  course_id: string;
  questions: QuizQuestion[];
  created_at: string;
}

export interface QuizQuestionResult {
  question_id: string;
  selected: number;
  correct_index: number;
  is_correct: boolean;
  explanation: string | null;
}

export interface QuizAttemptResult {
  id: string;
  quiz_id: string;
  score: number;
  total_questions: number;
  correct_count: number;
  results: QuizQuestionResult[];
  completed_at: string;
}

export interface QuizAttemptSummary {
  id: string;
  score: number;
  completed_at: string;
}

export interface QuizAttemptList {
  items: QuizAttemptSummary[];
  total: number;
}

export interface AiQuizQuestion {
  text: string;
  options: string[];
  correct_index: number;
  explanation: string;
}

export interface AiQuizResponse {
  lesson_id: string;
  questions: AiQuizQuestion[];
  model_used: string;
  cached: boolean;
}

export interface AiSummaryResponse {
  lesson_id: string;
  summary: string;
  model_used: string;
  cached: boolean;
}

export interface FlashcardData {
  id: string;
  course_id: string;
  concept: string;
  answer: string;
  source_type: string | null;
  stability: number;
  difficulty: number;
  due: string;
  state: number;
  reps: number;
  lapses: number;
  created_at: string;
}

export interface DueCardsResponse {
  items: FlashcardData[];
  total: number;
}

export interface ReviewResponse {
  card_id: string;
  rating: number;
  new_stability: number;
  new_difficulty: number;
  next_due: string;
  new_state: number;
}

export interface TutorChatResponse {
  session_id: string;
  message: string;
  model_used: string;
  credits_remaining: number;
}

export interface AiCreditsResponse {
  used: number;
  limit: number;
  remaining: number;
  reset_at: string;
  tier: "free" | "student" | "pro";
}

export interface TutorFeedbackResponse {
  status: string;
}

export interface ConceptData {
  id: string;
  course_id: string;
  lesson_id: string | null;
  name: string;
  description: string;
  parent_id: string | null;
  order: number;
  created_at: string;
  prerequisites: string[];
}

export interface CourseGraphResponse {
  concepts: ConceptData[];
}

export interface MasteryItem {
  concept_id: string;
  concept_name: string;
  mastery: number;
}

export interface CourseMasteryResponse {
  course_id: string;
  items: MasteryItem[];
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function requestVoid(url: string, options?: RequestInit): Promise<void> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

export interface PendingTeacher {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface PendingTeacherList {
  items: PendingTeacher[];
  total: number;
}

export const admin = {
  pendingTeachers(token: string) {
    return request<PendingTeacherList>(`${IDENTITY_URL}/admin/teachers/pending`, {
      headers: authHeaders(token),
    });
  },
  verifyTeacher(token: string, userId: string) {
    return request<User>(`${IDENTITY_URL}/admin/users/${userId}/verify`, {
      method: "PATCH",
      headers: authHeaders(token),
    });
  },
};

export const identity = {
  register(email: string, password: string, name: string, role: string = "student") {
    return request<TokenResponse>(`${IDENTITY_URL}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, name, role }),
    });
  },
  login(email: string, password: string) {
    return request<TokenResponse>(`${IDENTITY_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  },
  me(token: string) {
    return request<User>(`${IDENTITY_URL}/me`, {
      headers: authHeaders(token),
    });
  },
  verifyEmail(token: string) {
    return request<User>(`${IDENTITY_URL}/verify-email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
  },
  resendVerification(token: string) {
    return requestVoid(`${IDENTITY_URL}/resend-verification`, {
      method: "POST",
      headers: authHeaders(token),
    });
  },
  forgotPassword(email: string) {
    return requestVoid(`${IDENTITY_URL}/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
  },
  resetPassword(token: string, new_password: string) {
    return requestVoid(`${IDENTITY_URL}/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password }),
    });
  },
};

export const categories = {
  list() {
    return request<Category[]>(`${COURSE_URL}/categories`);
  },
};

export const courses = {
  list(params?: {
    q?: string;
    limit?: number;
    offset?: number;
    category_id?: string;
    level?: string;
    is_free?: boolean;
    sort_by?: string;
  }) {
    const sp = new URLSearchParams();
    if (params?.q) sp.set("q", params.q);
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    if (params?.category_id) sp.set("category_id", params.category_id);
    if (params?.level) sp.set("level", params.level);
    if (params?.is_free !== undefined) sp.set("is_free", String(params.is_free));
    if (params?.sort_by) sp.set("sort_by", params.sort_by);
    const qs = sp.toString();
    return request<CourseList>(`${COURSE_URL}/courses${qs ? `?${qs}` : ""}`);
  },
  get(id: string) {
    return request<Course>(`${COURSE_URL}/courses/${id}`);
  },
  create(token: string, data: {
    title: string;
    description: string;
    is_free: boolean;
    price?: number;
    duration_minutes: number;
    level: string;
  }) {
    return request<Course>(`${COURSE_URL}/courses`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  curriculum(id: string) {
    return request<CurriculumResponse>(`${COURSE_URL}/courses/${id}/curriculum`);
  },
  my(token: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<CourseList>(`${COURSE_URL}/courses/my${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
  update(token: string, id: string, data: {
    title?: string;
    description?: string;
    is_free?: boolean;
    price?: number;
    duration_minutes?: number;
    level?: string;
  }) {
    return request<Course>(`${COURSE_URL}/courses/${id}`, {
      method: "PUT",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
};

export const modules = {
  create(token: string, courseId: string, data: { title: string; order: number }) {
    return request<Module>(`${COURSE_URL}/courses/${courseId}/modules`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  update(token: string, moduleId: string, data: { title?: string; order?: number }) {
    return request<Module>(`${COURSE_URL}/modules/${moduleId}`, {
      method: "PUT",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  delete(token: string, moduleId: string) {
    return requestVoid(`${COURSE_URL}/modules/${moduleId}`, {
      method: "DELETE",
      headers: authHeaders(token),
    });
  },
};

export const lessons = {
  create(token: string, moduleId: string, data: {
    title: string;
    content?: string;
    video_url?: string;
    duration_minutes?: number;
    order?: number;
  }) {
    return request<Lesson>(`${COURSE_URL}/modules/${moduleId}/lessons`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  get(id: string) {
    return request<Lesson>(`${COURSE_URL}/lessons/${id}`);
  },
  update(token: string, lessonId: string, data: {
    title?: string;
    content?: string;
    video_url?: string;
    duration_minutes?: number;
    order?: number;
  }) {
    return request<Lesson>(`${COURSE_URL}/lessons/${lessonId}`, {
      method: "PUT",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  delete(token: string, lessonId: string) {
    return requestVoid(`${COURSE_URL}/lessons/${lessonId}`, {
      method: "DELETE",
      headers: authHeaders(token),
    });
  },
};

export const reviews = {
  create(token: string, data: { course_id: string; rating: number; comment?: string }) {
    return request<Review>(`${COURSE_URL}/reviews`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  byCourse(courseId: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<ReviewList>(`${COURSE_URL}/reviews/course/${courseId}${qs ? `?${qs}` : ""}`);
  },
};

export const progress = {
  complete(token: string, lessonId: string, courseId: string) {
    return request<{ id: string; lesson_id: string; course_id: string; completed_at: string }>(
      `${ENROLLMENT_URL}/progress/lessons/${lessonId}/complete`,
      {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify({ course_id: courseId }),
      },
    );
  },
  course(token: string, courseId: string, totalLessons: number) {
    return request<CourseProgress>(
      `${ENROLLMENT_URL}/progress/courses/${courseId}?total_lessons=${totalLessons}`,
      { headers: authHeaders(token) },
    );
  },
  completedLessons(token: string, courseId: string) {
    return request<{ course_id: string; completed_lesson_ids: string[] }>(
      `${ENROLLMENT_URL}/progress/courses/${courseId}/lessons`,
      { headers: authHeaders(token) },
    );
  },
};

export const enrollments = {
  create(token: string, data: { course_id: string; payment_id?: string; total_lessons?: number }) {
    return request<Enrollment>(`${ENROLLMENT_URL}/enrollments`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  me(token: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<EnrollmentList>(`${ENROLLMENT_URL}/enrollments/me${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
  courseCount(courseId: string) {
    return request<{ course_id: string; count: number }>(
      `${ENROLLMENT_URL}/enrollments/course/${courseId}/count`,
    );
  },
};

export const payments = {
  create(token: string, data: { course_id: string; amount: number }) {
    return request<Payment>(`${PAYMENT_URL}/payments`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  get(token: string, id: string) {
    return request<Payment>(`${PAYMENT_URL}/payments/${id}`, {
      headers: authHeaders(token),
    });
  },
  me(token: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<PaymentList>(`${PAYMENT_URL}/payments/me${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
};

export interface SubscriptionPlan {
  id: string;
  name: "free" | "student" | "pro";
  stripe_price_id: string | null;
  price_monthly: number;
  price_yearly: number | null;
  ai_credits_daily: number;
  features: Record<string, unknown>;
  created_at: string;
}

export interface UserSubscription {
  id: string;
  user_id: string;
  plan_id: string;
  plan_name: "free" | "student" | "pro";
  stripe_subscription_id: string | null;
  stripe_customer_id: string | null;
  status: "active" | "canceled" | "past_due";
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  created_at: string;
  updated_at: string;
}

export const subscriptions = {
  plans() {
    return request<SubscriptionPlan[]>(`${PAYMENT_URL}/subscriptions/plans`);
  },
  me(token: string) {
    return request<UserSubscription>(`${PAYMENT_URL}/subscriptions/me`, {
      headers: authHeaders(token),
    });
  },
  create(token: string, data: { plan_id: string; payment_method_id: string }) {
    return request<UserSubscription>(`${PAYMENT_URL}/subscriptions`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  cancel(token: string) {
    return request<UserSubscription>(`${PAYMENT_URL}/subscriptions/cancel`, {
      method: "POST",
      headers: authHeaders(token),
    });
  },
};

export const notifications = {
  create(token: string, data: { type: string; title: string; body?: string }) {
    return request<Notification>(`${NOTIFICATION_URL}/notifications`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  me(token: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<NotificationList>(`${NOTIFICATION_URL}/notifications/me${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
  markRead(token: string, id: string) {
    return request<Notification>(`${NOTIFICATION_URL}/notifications/${id}/read`, {
      method: "PATCH",
      headers: authHeaders(token),
    });
  },
};

export const ai = {
  generateQuiz(token: string, lessonId: string, content: string) {
    return request<AiQuizResponse>(`${AI_URL}/ai/quiz/generate`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ lesson_id: lessonId, content }),
    });
  },
  generateSummary(token: string, lessonId: string, content: string) {
    return request<AiSummaryResponse>(`${AI_URL}/ai/summary/generate`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ lesson_id: lessonId, content }),
    });
  },
  tutorChat(token: string, data: {
    lesson_id: string;
    message: string;
    lesson_content: string;
    session_id?: string;
  }) {
    return request<TutorChatResponse>(`${AI_URL}/ai/tutor/chat`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  tutorFeedback(token: string, data: {
    session_id: string;
    message_index: number;
    rating: number;
  }) {
    return request<TutorFeedbackResponse>(`${AI_URL}/ai/tutor/feedback`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  credits(token: string) {
    return request<AiCreditsResponse>(`${AI_URL}/ai/credits/me`, {
      headers: authHeaders(token),
    });
  },
};

export const quizzes = {
  getByLesson(token: string, lessonId: string) {
    return request<QuizData>(`${LEARNING_URL}/quizzes/lesson/${lessonId}`, {
      headers: authHeaders(token),
    });
  },
  create(token: string, data: { lesson_id: string; course_id: string; questions: AiQuizQuestion[] }) {
    return request<QuizData>(`${LEARNING_URL}/quizzes`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  submit(token: string, quizId: string, answers: number[]) {
    return request<QuizAttemptResult>(`${LEARNING_URL}/quizzes/${quizId}/submit`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ answers }),
    });
  },
  myAttempts(token: string, quizId: string) {
    return request<QuizAttemptList>(`${LEARNING_URL}/quizzes/${quizId}/attempts/me`, {
      headers: authHeaders(token),
    });
  },
};

export const flashcards = {
  create(token: string, data: { course_id: string; concept: string; answer: string; source_type?: string; source_id?: string }) {
    return request<FlashcardData>(`${LEARNING_URL}/flashcards`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  due(token: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<DueCardsResponse>(`${LEARNING_URL}/flashcards/due${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
  review(token: string, cardId: string, data: { rating: number; review_duration_ms?: number }) {
    return request<ReviewResponse>(`${LEARNING_URL}/flashcards/${cardId}/review`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  delete(token: string, cardId: string) {
    return requestVoid(`${LEARNING_URL}/flashcards/${cardId}`, {
      method: "DELETE",
      headers: authHeaders(token),
    });
  },
};

export interface XpEventData {
  action: string;
  points: number;
  course_id: string | null;
  created_at: string;
}

export interface XpSummaryResponse {
  total_xp: number;
  events: XpEventData[];
}

export interface BadgeData {
  badge_type: string;
  description: string;
  unlocked_at: string;
}

export interface BadgeListResponse {
  badges: BadgeData[];
  total: number;
}

export interface StreakData {
  current_streak: number;
  longest_streak: number;
  last_activity_date: string | null;
  active_today: boolean;
}

export const xp = {
  me(token: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<XpSummaryResponse>(`${LEARNING_URL}/xp/me${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
};

export const badges = {
  me(token: string) {
    return request<BadgeListResponse>(`${LEARNING_URL}/badges/me`, {
      headers: authHeaders(token),
    });
  },
};

export const streaks = {
  me(token: string) {
    return request<StreakData>(`${LEARNING_URL}/streaks/me`, {
      headers: authHeaders(token),
    });
  },
};

export interface PretestStartResponse {
  pretest_id: string;
  question: string;
  concept_id: string;
  answer_id: string;
  total_concepts: number;
}

export interface ConceptResult {
  concept_id: string;
  name: string;
  mastery: number;
  tested: boolean;
}

export interface PretestResultsResponse {
  course_id: string;
  concepts: ConceptResult[];
  overall_readiness: number;
}

export interface AnswerNextResponse {
  next_question: string | null;
  concept_id: string | null;
  answer_id: string | null;
  progress: number;
  completed: boolean;
  results: PretestResultsResponse | null;
}

export const pretests = {
  start(token: string, courseId: string) {
    return request<PretestStartResponse>(`${LEARNING_URL}/pretests/course/${courseId}/start`, {
      method: "POST",
      headers: authHeaders(token),
    });
  },
  answer(token: string, pretestId: string, data: { answer_id: string; answer: string }) {
    return request<AnswerNextResponse>(`${LEARNING_URL}/pretests/${pretestId}/answer`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  results(token: string, courseId: string) {
    return request<PretestResultsResponse>(`${LEARNING_URL}/pretests/course/${courseId}/results`, {
      headers: authHeaders(token),
    });
  },
};

export const concepts = {
  getCourseGraph(token: string, courseId: string) {
    return request<CourseGraphResponse>(`${LEARNING_URL}/concepts/course/${courseId}`, {
      headers: authHeaders(token),
    });
  },
  getCourseMastery(token: string, courseId: string) {
    return request<CourseMasteryResponse>(`${LEARNING_URL}/concepts/mastery/course/${courseId}`, {
      headers: authHeaders(token),
    });
  },
  create(token: string, data: { course_id: string; name: string; description?: string; lesson_id?: string; parent_id?: string; order?: number }) {
    return request<ConceptData>(`${LEARNING_URL}/concepts`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  update(token: string, conceptId: string, data: { name?: string; description?: string; lesson_id?: string; parent_id?: string; order?: number }) {
    return request<ConceptData>(`${LEARNING_URL}/concepts/${conceptId}`, {
      method: "PUT",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  delete(token: string, conceptId: string) {
    return requestVoid(`${LEARNING_URL}/concepts/${conceptId}`, {
      method: "DELETE",
      headers: authHeaders(token),
    });
  },
  addPrerequisite(token: string, conceptId: string, prerequisiteId: string) {
    return request<{ status: string }>(`${LEARNING_URL}/concepts/${conceptId}/prerequisites`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ prerequisite_id: prerequisiteId }),
    });
  },
};
