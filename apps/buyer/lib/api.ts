const IDENTITY_URL = "/api/identity";
const COURSE_URL = "/api/course";
const ENROLLMENT_URL = "/api/enrollment";
const PAYMENT_URL = "/api/payment";
const NOTIFICATION_URL = "/api/notification";
const AI_URL = "/api/ai";
const LEARNING_URL = "/api/learning";
const RAG_URL = "/api/rag";

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

export interface PublicProfile {
  id: string;
  name: string;
  bio: string | null;
  avatar_url: string | null;
  role: "student" | "teacher" | "admin";
  is_verified: boolean;
  created_at: string;
  is_public: boolean;
}

export interface UserStats {
  name: string;
  role: string;
  is_verified: boolean;
  member_since: string;
}

export interface FollowCounts {
  followers_count: number;
  following_count: number;
}

export interface FollowItem {
  id: string;
  follower_id: string;
  following_id: string;
  created_at: string;
}

export interface FollowList {
  items: FollowItem[];
  total: number;
}

export const profiles = {
  get(userId: string) {
    return request<PublicProfile>(`${IDENTITY_URL}/users/${userId}/profile`);
  },
  stats(userId: string) {
    return request<UserStats>(`${IDENTITY_URL}/users/${userId}/stats`);
  },
  followCounts(userId: string) {
    return request<FollowCounts>(`${IDENTITY_URL}/users/${userId}/followers/count`);
  },
  follow(token: string, userId: string) {
    return requestVoid(`${IDENTITY_URL}/follow/${userId}`, {
      method: "POST",
      headers: authHeaders(token),
    });
  },
  unfollow(token: string, userId: string) {
    return requestVoid(`${IDENTITY_URL}/follow/${userId}`, {
      method: "DELETE",
      headers: authHeaders(token),
    });
  },
  myFollowing(token: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<FollowList>(`${IDENTITY_URL}/following/me${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
  myFollowers(token: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<FollowList>(`${IDENTITY_URL}/followers/me${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
};

export interface ReferralStats {
  referral_code: string;
  invited_count: number;
  completed_count: number;
  rewards_earned: number;
}

export interface Referral {
  id: string;
  referrer_id: string;
  referee_id: string;
  status: string;
  created_at: string;
}

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
  getReferralInfo(token: string) {
    return request<ReferralStats>(`${IDENTITY_URL}/referral/me`, {
      headers: authHeaders(token),
    });
  },
  applyReferralCode(token: string, data: { referral_code: string }) {
    return request<Referral>(`${IDENTITY_URL}/referral/apply`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
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

export interface DiscountResult {
  original_price: number;
  discount_amount: number;
  final_price: number;
  coupon_code: string;
}

export const coupons = {
  validate(token: string, data: { code: string; course_id: string; amount: number }) {
    return request<DiscountResult>(`${PAYMENT_URL}/coupons/validate`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
};

export const payments = {
  create(token: string, data: { course_id: string; amount: number; coupon_code?: string }) {
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

export interface ConversationPreview {
  conversation_id: string;
  other_user_id: string;
  last_message_content: string;
  last_message_at: string;
  unread_count: number;
}

export interface ConversationList {
  items: ConversationPreview[];
  total: number;
}

export interface DirectMessage {
  id: string;
  conversation_id: string;
  sender_id: string;
  content: string;
  is_read: boolean;
  created_at: string;
}

export interface DirectMessageList {
  items: DirectMessage[];
  total: number;
}

export const messaging = {
  sendMessage(token: string, data: { recipient_id: string; content: string }) {
    return request<DirectMessage>(`${NOTIFICATION_URL}/messages`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  getConversations(token: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<ConversationList>(`${NOTIFICATION_URL}/conversations/me${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
  getMessages(token: string, conversationId: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<DirectMessageList>(`${NOTIFICATION_URL}/conversations/${conversationId}/messages${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
  markRead(token: string, messageId: string) {
    return requestVoid(`${NOTIFICATION_URL}/messages/${messageId}/read`, {
      method: "PATCH",
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

export interface CourseBundle {
  id: string;
  teacher_id: string;
  title: string;
  description: string;
  price: number;
  discount_percent: number;
  is_active: boolean;
  created_at: string;
}

export interface BundleList {
  items: CourseBundle[];
  total: number;
}

export interface BundleWithCourses extends CourseBundle {
  courses: Course[];
}

export const bundles = {
  list(params?: { limit?: number; offset?: number; teacher_id?: string }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    if (params?.teacher_id) sp.set("teacher_id", params.teacher_id);
    const qs = sp.toString();
    return request<BundleList>(`${COURSE_URL}/bundles${qs ? `?${qs}` : ""}`);
  },
  get(id: string) {
    return request<BundleWithCourses>(`${COURSE_URL}/bundles/${id}`);
  },
};

export interface QuizScoreTrend {
  week: string;
  avg_score: number;
}

export interface VelocityCourseProgress {
  course_id: string;
  total_concepts: number;
  mastered: number;
  mastery_pct: number;
  estimated_weeks_left: number;
}

export interface VelocityResponse {
  concepts_mastered_this_week: number;
  concepts_mastered_last_week: number;
  trend: "up" | "down" | "stable";
  quiz_score_trend: QuizScoreTrend[];
  flashcard_retention_rate: number;
  streak_days: number;
  course_progress: VelocityCourseProgress[];
}

export const velocity = {
  me(token: string) {
    return request<VelocityResponse>(`${LEARNING_URL}/velocity/me`, {
      headers: authHeaders(token),
    });
  },
};

export interface StudyGroup {
  id: string;
  course_id: string;
  name: string;
  description: string | null;
  creator_id: string;
  max_members: number;
  created_at: string;
}

export interface StudyGroupWithCount extends StudyGroup {
  member_count: number;
}

export interface StudyGroupList {
  items: StudyGroupWithCount[];
  total: number;
}

export interface GroupMember {
  id: string;
  group_id: string;
  user_id: string;
  joined_at: string;
}

export interface GroupMemberList {
  items: GroupMember[];
  total: number;
}

export const studyGroups = {
  byCourse(courseId: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<StudyGroupList>(`${LEARNING_URL}/study-groups/course/${courseId}${qs ? `?${qs}` : ""}`);
  },
  create(token: string, data: { course_id: string; name: string; description?: string }) {
    return request<StudyGroup>(`${LEARNING_URL}/study-groups`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(data),
    });
  },
  join(token: string, groupId: string) {
    return request<GroupMember>(`${LEARNING_URL}/study-groups/${groupId}/join`, {
      method: "POST",
      headers: authHeaders(token),
    });
  },
  leave(token: string, groupId: string) {
    return requestVoid(`${LEARNING_URL}/study-groups/${groupId}/leave`, {
      method: "DELETE",
      headers: authHeaders(token),
    });
  },
  members(groupId: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<GroupMemberList>(`${LEARNING_URL}/study-groups/${groupId}/members${qs ? `?${qs}` : ""}`);
  },
  me(token: string) {
    return request<StudyGroup[]>(`${LEARNING_URL}/study-groups/me`, {
      headers: authHeaders(token),
    });
  },
};

export interface Activity {
  id: string;
  user_id: string;
  activity_type: "quiz_completed" | "flashcard_reviewed" | "badge_earned" | "streak_milestone" | "concept_mastered";
  payload: Record<string, unknown>;
  created_at: string;
}

export interface ActivityList {
  items: Activity[];
  total: number;
}

export const activity = {
  me(token: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<ActivityList>(`${LEARNING_URL}/activity/me${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
  feed(token: string, params: { user_ids: string[]; limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    sp.set("user_ids", params.user_ids.join(","));
    if (params.limit) sp.set("limit", String(params.limit));
    if (params.offset) sp.set("offset", String(params.offset));
    return request<ActivityList>(`${LEARNING_URL}/activity/feed?${sp.toString()}`, {
      headers: authHeaders(token),
    });
  },
};

export interface CoEnrollmentRecommendation {
  course_id: string;
  co_enrollment_count: number;
}

export interface PersonalRecommendation {
  course_id: string;
  relevance_score: number;
}

export const recommendations = {
  forCourse(courseId: string) {
    return request<CoEnrollmentRecommendation[]>(
      `${ENROLLMENT_URL}/recommendations/courses/${courseId}`,
    );
  },
  forMe(token: string) {
    return request<PersonalRecommendation[]>(
      `${ENROLLMENT_URL}/recommendations/me`,
      { headers: authHeaders(token) },
    );
  },
};

export interface WishlistItem {
  id: string;
  student_id: string;
  course_id: string;
  created_at: string;
  course: Course;
}

export interface WishlistList {
  items: WishlistItem[];
  total: number;
}

export interface WishlistCheck {
  in_wishlist: boolean;
}

export const wishlist = {
  add(token: string, courseId: string) {
    return request<WishlistItem>(`${COURSE_URL}/wishlist`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ course_id: courseId }),
    });
  },
  remove(token: string, courseId: string) {
    return requestVoid(`${COURSE_URL}/wishlist/${courseId}`, {
      method: "DELETE",
      headers: authHeaders(token),
    });
  },
  me(token: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<WishlistList>(`${COURSE_URL}/wishlist/me${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
  check(token: string, courseId: string) {
    return request<WishlistCheck>(`${COURSE_URL}/wishlist/check/${courseId}`, {
      headers: authHeaders(token),
    });
  },
};

export interface MissionBlueprint {
  concept_name: string;
  reading_content: string;
  check_questions: unknown[];
  code_case: unknown | null;
  recap_questions: unknown[];
}

export interface Mission {
  id: string;
  concept_id: string;
  mission_type: string;
  status: "pending" | "in_progress" | "completed";
  blueprint: MissionBlueprint | null;
  score: number | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface TrustLevel {
  level: number;
  total_missions_completed: number;
  total_concepts_mastered: number;
  unlocked_areas: string[];
}

export interface TrustLevelWithUser extends TrustLevel {
  user_id: string;
}

export interface TrustLevelListResponse {
  levels: TrustLevelWithUser[];
}

export const trustLevels = {
  getOrgLevels(token: string, orgId: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<TrustLevelListResponse>(`${LEARNING_URL}/trust-level/org/${orgId}${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
};

export interface DailySummary {
  mission: Mission | null;
  trust_level: TrustLevel;
  due_flashcards: number;
  streak_days: number;
  greeting: string;
}

export type CoachPhase = "recap" | "reading" | "questions" | "code_case" | "wrap_up";

export interface CoachStartResponse {
  session_id: string;
  greeting: string;
  phase: CoachPhase;
}

export interface CoachChatResponse {
  reply: string;
  phase: CoachPhase;
  progress: number;
  hint?: string;
}

export interface CoachEndResponse {
  summary: string;
  score: number;
  mastery_delta: number;
  strengths: string[];
  gaps: string[];
}

export interface MissionStartResponse {
  session_id: string;
  first_question: string;
}

export interface MissionCompleteResponse {
  score: number;
  mastery_delta: number;
  strengths: string[];
  gaps: string[];
}

export interface MissionHistoryList {
  items: Mission[];
  total: number;
}

export interface MissionStreakResponse {
  current_streak: number;
  longest_streak: number;
}

export const daily = {
  getSummary(token: string) {
    return request<DailySummary>(`${AI_URL}/ai/mission/daily`, {
      headers: authHeaders(token),
    });
  },
};

export const missions = {
  start(token: string, missionId: string) {
    return request<MissionStartResponse>(`${AI_URL}/ai/mission/${missionId}/start`, {
      method: "POST",
      headers: authHeaders(token),
    });
  },
  complete(token: string, missionId: string, sessionId: string) {
    return request<MissionCompleteResponse>(`${AI_URL}/ai/mission/${missionId}/complete`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ session_id: sessionId }),
    });
  },
  getHistory(token: string, params?: { limit?: number; offset?: number }) {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.offset) sp.set("offset", String(params.offset));
    const qs = sp.toString();
    return request<MissionHistoryList>(`${AI_URL}/ai/missions/me${qs ? `?${qs}` : ""}`, {
      headers: authHeaders(token),
    });
  },
  getStreak(token: string) {
    return request<MissionStreakResponse>(`${AI_URL}/ai/missions/streak`, {
      headers: authHeaders(token),
    });
  },
};

export const coach = {
  startSession(token: string, missionId: string) {
    return request<CoachStartResponse>(`${AI_URL}/ai/coach/start`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ mission_id: missionId }),
    });
  },
  sendMessage(token: string, sessionId: string, message: string) {
    return request<CoachChatResponse>(`${AI_URL}/ai/coach/chat`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  },
  endSession(token: string, sessionId: string) {
    return request<CoachEndResponse>(`${AI_URL}/ai/coach/end`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ session_id: sessionId }),
    });
  },
};

export interface Organization {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  settings: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

export interface OrgMember {
  id: string;
  organization_id: string;
  user_id: string;
  role: string;
  joined_at: string;
}

export const organizations = {
  getMyOrgs(token: string) {
    return request<Organization[]>(`${IDENTITY_URL}/organizations/me`, {
      headers: authHeaders(token),
    });
  },
  getOrg(token: string, id: string) {
    return request<Organization>(`${IDENTITY_URL}/organizations/${id}`, {
      headers: authHeaders(token),
    });
  },
  getMembers(token: string, id: string) {
    return request<OrgMember[]>(`${IDENTITY_URL}/organizations/${id}/members`, {
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

export interface KbSearchResult {
  chunk_id: string;
  content: string;
  similarity: number;
  document_title: string | null;
  source_type: string | null;
  source_path: string | null;
  metadata: Record<string, unknown> | null;
}

export interface ExternalSearchResult {
  title: string;
  url: string;
  snippet: string;
  domain: string;
}

export interface ExternalSearchResponse {
  results: ExternalSearchResult[];
}

export const kb = {
  search(token: string, orgId: string, query: string, limit: number = 5) {
    return request<KbSearchResult[]>(`${RAG_URL}/kb/${orgId}/search`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ query, limit }),
    });
  },
};

export const externalSearch = {
  search(token: string, query: string, limit: number = 5) {
    return request<ExternalSearchResponse>(`${AI_URL}/ai/search/external`, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ query, limit }),
    });
  },
};
