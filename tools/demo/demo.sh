#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# EduPlatform Demo Script — full user journey via curl + browser
# Prerequisites: docker compose dev running, seed data loaded, frontend on :3001
# Usage: ./tools/demo/demo.sh
# =============================================================================

IDENTITY=http://localhost:8001
COURSE=http://localhost:8002
ENROLLMENT=http://localhost:8003
PAYMENT=http://localhost:8004
NOTIFICATION=http://localhost:8005
AI=http://localhost:8006
LEARNING=http://localhost:8007
FRONTEND=http://localhost:3001

DEMO_DELAY=${DEMO_DELAY:-1}
BROWSER_DELAY=${BROWSER_DELAY:-3}
TS=$(date +%s)
STEP_NUM=0

# Colors
Y='\033[1;33m'
G='\033[1;32m'
R='\033[1;31m'
C='\033[1;36m'
B='\033[1m'
N='\033[0m'

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

header() {
    echo ""
    echo -e "${Y}======================================================================${N}"
    echo -e "${Y}  $1${N}"
    echo -e "${Y}======================================================================${N}"
}

step() {
    STEP_NUM=$((STEP_NUM + 1))
    echo ""
    echo -e "${C}  [${STEP_NUM}] $1${N}"
}

pause() {
    sleep "$DEMO_DELAY"
}

# Open a URL in the browser (WSL2 → wslview, Linux → xdg-open, macOS → open)
browse() {
    local url="$1"
    local label="${2:-}"
    echo -e "  ${G}>>> Browser: ${url}${N}"
    if [[ -n "$label" ]]; then
        echo -e "  ${G}    ${label}${N}"
    fi
    if command -v wslview &>/dev/null; then
        wslview "$url" &>/dev/null &
    elif command -v xdg-open &>/dev/null; then
        xdg-open "$url" &>/dev/null &
    elif command -v open &>/dev/null; then
        open "$url" &>/dev/null &
    fi
    sleep "$BROWSER_DELAY"
}

# call METHOD URL [DATA] [AUTH_TOKEN]
call() {
    local method="$1"
    local url="$2"
    local data="${3:-}"
    local token="${4:-}"

    local -a args=(-s -w '\n%{http_code}' -X "$method")
    args+=(-H 'Content-Type: application/json')

    if [[ -n "$token" ]]; then
        args+=(-H "Authorization: Bearer $token")
    fi
    if [[ -n "$data" ]]; then
        args+=(-d "$data")
    fi

    local raw
    raw=$(curl "${args[@]}" "$url")

    local http_code
    http_code=$(echo "$raw" | tail -1)
    local body
    body=$(echo "$raw" | sed '$d')

    echo -e "  ${B}${method} ${url}${N}  -> ${B}HTTP ${http_code}${N}"

    if [[ -n "$body" ]]; then
        echo "$body" | jq . 2>/dev/null || echo "$body"
    fi

    if [[ "$http_code" -lt 200 || "$http_code" -ge 300 ]]; then
        echo -e "${R}  FAILED (HTTP ${http_code}). Aborting.${N}"
        exit 1
    fi

    LAST_BODY="$body"
    LAST_CODE="$http_code"
    pause
}

extract_email_token() {
    docker compose -f docker-compose.dev.yml logs identity 2>&1 \
        | grep "\[EMAIL_VERIFY\]" | tail -1 | sed 's/.*token=//'
}

extract_reset_token() {
    docker compose -f docker-compose.dev.yml logs identity 2>&1 \
        | grep "\[PASSWORD_RESET\]" | tail -1 | sed 's/.*token=//'
}

jq_field() {
    echo "$LAST_BODY" | jq -r "$1"
}

# ---------------------------------------------------------------------------
# 0. Health check
# ---------------------------------------------------------------------------

header "0. Health Check — all services"

for svc_name in identity course enrollment payment notification ai learning; do
    case "$svc_name" in
        identity)     svc_url="$IDENTITY" ;;
        course)       svc_url="$COURSE" ;;
        enrollment)   svc_url="$ENROLLMENT" ;;
        payment)      svc_url="$PAYMENT" ;;
        notification) svc_url="$NOTIFICATION" ;;
        ai)           svc_url="$AI" ;;
        learning)     svc_url="$LEARNING" ;;
    esac
    step "$svc_name /health/ready"
    call GET "${svc_url}/health/ready"
done

# ---------------------------------------------------------------------------
# 1. Student registration + email verification
# ---------------------------------------------------------------------------

STUDENT_EMAIL="demo-student-${TS}@test.com"
STUDENT_PASS="demo123"

header "1. Student Registration + Email Verification"

browse "$FRONTEND/register" "Opening registration page..."

step "Register student"
call POST "$IDENTITY/register" \
    "{\"email\":\"${STUDENT_EMAIL}\",\"password\":\"${STUDENT_PASS}\",\"name\":\"Demo Student\",\"role\":\"student\"}"
STUDENT_TOKEN=$(jq_field '.access_token')
STUDENT_REFRESH=$(jq_field '.refresh_token')

step "GET /me — email_verified should be false"
call GET "$IDENTITY/me" "" "$STUDENT_TOKEN"

step "Extract email verification token from Docker logs"
EMAIL_TOKEN=$(extract_email_token)
if [[ -z "$EMAIL_TOKEN" ]]; then
    echo -e "${R}  Could not extract email token from logs. Aborting.${N}"
    exit 1
fi
echo -e "  Token: ${B}${EMAIL_TOKEN}${N}"

step "Verify email"
call POST "$IDENTITY/verify-email" "{\"token\":\"${EMAIL_TOKEN}\"}"

browse "$FRONTEND/verify-email?token=${EMAIL_TOKEN}" "Opening email verification page..."

step "GET /me — email_verified should be true"
call GET "$IDENTITY/me" "" "$STUDENT_TOKEN"

# ---------------------------------------------------------------------------
# 2. Teacher registration + admin verification
# ---------------------------------------------------------------------------

TEACHER_EMAIL="demo-teacher-${TS}@test.com"
TEACHER_PASS="demo123"

header "2. Teacher Registration + Admin Verification"

step "Register teacher"
call POST "$IDENTITY/register" \
    "{\"email\":\"${TEACHER_EMAIL}\",\"password\":\"${TEACHER_PASS}\",\"name\":\"Demo Teacher\",\"role\":\"teacher\"}"
TEACHER_TOKEN=$(jq_field '.access_token')

step "GET /me — is_verified should be false"
call GET "$IDENTITY/me" "" "$TEACHER_TOKEN"
TEACHER_ID=$(jq_field '.id')

step "Login as admin"
call POST "$IDENTITY/login" \
    '{"email":"admin@eduplatform.com","password":"password"}'
ADMIN_TOKEN=$(jq_field '.access_token')

browse "$FRONTEND/admin/teachers" "Opening admin panel — pending teachers..."

step "GET /admin/teachers/pending"
call GET "$IDENTITY/admin/teachers/pending?limit=5" "" "$ADMIN_TOKEN"

step "PATCH /admin/users/${TEACHER_ID}/verify"
call PATCH "$IDENTITY/admin/users/${TEACHER_ID}/verify" "" "$ADMIN_TOKEN"

step "Re-login teacher to get fresh token with is_verified: true"
call POST "$IDENTITY/login" \
    "{\"email\":\"${TEACHER_EMAIL}\",\"password\":\"${TEACHER_PASS}\"}"
TEACHER_TOKEN=$(jq_field '.access_token')

step "GET /me — teacher verified"
call GET "$IDENTITY/me" "" "$TEACHER_TOKEN"

# ---------------------------------------------------------------------------
# 3. Teacher creates a course
# ---------------------------------------------------------------------------

header "3. Teacher Creates a Course"

step "GET /categories"
call GET "$COURSE/categories"
CATEGORY_ID=$(echo "$LAST_BODY" | jq -r '.[0].id')
CATEGORY_NAME=$(echo "$LAST_BODY" | jq -r '.[0].name')
echo -e "  Using category: ${B}${CATEGORY_NAME}${N} (${CATEGORY_ID})"

browse "$FRONTEND/courses/new" "Opening 'Create Course' page..."

step "POST /courses — create course"
call POST "$COURSE/courses" \
    "{\"title\":\"Demo Course ${TS}\",\"description\":\"A demo course for testing the platform\",\"is_free\":true,\"level\":\"beginner\",\"category_id\":\"${CATEGORY_ID}\"}" \
    "$TEACHER_TOKEN"
COURSE_ID=$(jq_field '.id')
echo -e "  Course ID: ${B}${COURSE_ID}${N}"

step "POST /courses/${COURSE_ID}/modules — Module 1"
call POST "$COURSE/courses/${COURSE_ID}/modules" \
    '{"title":"Getting Started","order":1}' \
    "$TEACHER_TOKEN"
MODULE1_ID=$(jq_field '.id')

step "POST /courses/${COURSE_ID}/modules — Module 2"
call POST "$COURSE/courses/${COURSE_ID}/modules" \
    '{"title":"Advanced Topics","order":2}' \
    "$TEACHER_TOKEN"
MODULE2_ID=$(jq_field '.id')

step "POST /modules/${MODULE1_ID}/lessons — Lesson 1"
call POST "$COURSE/modules/${MODULE1_ID}/lessons" \
    '{"title":"Introduction","content":"Welcome to the course!","duration_minutes":10,"order":1}' \
    "$TEACHER_TOKEN"
LESSON1_ID=$(jq_field '.id')

step "POST /modules/${MODULE1_ID}/lessons — Lesson 2"
call POST "$COURSE/modules/${MODULE1_ID}/lessons" \
    '{"title":"Setup Environment","content":"Install required tools","duration_minutes":15,"order":2}' \
    "$TEACHER_TOKEN"
LESSON2_ID=$(jq_field '.id')

step "POST /modules/${MODULE2_ID}/lessons — Lesson 3"
call POST "$COURSE/modules/${MODULE2_ID}/lessons" \
    '{"title":"Deep Dive","content":"Advanced concepts explained","duration_minutes":20,"order":1}' \
    "$TEACHER_TOKEN"
LESSON3_ID=$(jq_field '.id')

step "GET /courses/${COURSE_ID}/curriculum"
call GET "$COURSE/courses/${COURSE_ID}/curriculum"
TOTAL_LESSONS=$(jq_field '.total_lessons')
echo -e "  Total lessons: ${B}${TOTAL_LESSONS}${N}"

browse "$FRONTEND/courses/${COURSE_ID}" "Opening course page — see curriculum..."

# ---------------------------------------------------------------------------
# 4. Student takes the course
# ---------------------------------------------------------------------------

header "4. Student Takes the Course"

browse "$FRONTEND/courses?level=beginner&is_free=true" "Opening catalog — free beginner courses..."

step "GET /courses — filter free beginner courses"
call GET "$COURSE/courses?level=beginner&is_free=true&limit=5"

step "GET /courses/${COURSE_ID} — course details"
call GET "$COURSE/courses/${COURSE_ID}"

step "GET /enrollments/course/${COURSE_ID}/count — enrollment count before"
call GET "$ENROLLMENT/enrollments/course/${COURSE_ID}/count"

step "POST /enrollments — enroll in course"
call POST "$ENROLLMENT/enrollments" \
    "{\"course_id\":\"${COURSE_ID}\",\"total_lessons\":${TOTAL_LESSONS}}" \
    "$STUDENT_TOKEN"
ENROLLMENT_ID=$(jq_field '.id')

step "POST /notifications — enrollment notification"
call POST "$NOTIFICATION/notifications" \
    "{\"type\":\"enrollment\",\"title\":\"Enrolled in Demo Course\",\"body\":\"You have successfully enrolled!\"}" \
    "$STUDENT_TOKEN"
NOTIF_ID=$(jq_field '.id')

browse "$FRONTEND/enrollments" "Opening 'My Enrollments' page..."

step "GET /enrollments/me"
call GET "$ENROLLMENT/enrollments/me" "" "$STUDENT_TOKEN"

browse "$FRONTEND/courses/${COURSE_ID}/lessons/${LESSON1_ID}" "Opening Lesson 1..."

step "Complete lesson 1"
call POST "$ENROLLMENT/progress/lessons/${LESSON1_ID}/complete" \
    "{\"course_id\":\"${COURSE_ID}\"}" \
    "$STUDENT_TOKEN"

step "GET progress — should be ~33%"
call GET "$ENROLLMENT/progress/courses/${COURSE_ID}?total_lessons=${TOTAL_LESSONS}" "" "$STUDENT_TOKEN"

step "Complete lesson 2"
call POST "$ENROLLMENT/progress/lessons/${LESSON2_ID}/complete" \
    "{\"course_id\":\"${COURSE_ID}\"}" \
    "$STUDENT_TOKEN"

step "Complete lesson 3 — should trigger auto-completion"
call POST "$ENROLLMENT/progress/lessons/${LESSON3_ID}/complete" \
    "{\"course_id\":\"${COURSE_ID}\"}" \
    "$STUDENT_TOKEN"

step "GET progress — should be 100%"
call GET "$ENROLLMENT/progress/courses/${COURSE_ID}?total_lessons=${TOTAL_LESSONS}" "" "$STUDENT_TOKEN"

browse "$FRONTEND/enrollments" "Opening enrollments — course should be COMPLETED..."

step "GET /enrollments/me — status should be COMPLETED"
call GET "$ENROLLMENT/enrollments/me" "" "$STUDENT_TOKEN"

step "POST /reviews — leave a review"
call POST "$COURSE/reviews" \
    "{\"course_id\":\"${COURSE_ID}\",\"rating\":5,\"comment\":\"Excellent demo course!\"}" \
    "$STUDENT_TOKEN"

step "GET /reviews/course/${COURSE_ID}"
call GET "$COURSE/reviews/course/${COURSE_ID}"

browse "$FRONTEND/courses/${COURSE_ID}" "Opening course page — check rating and reviews..."

step "GET /courses/${COURSE_ID} — avg_rating should be updated"
call GET "$COURSE/courses/${COURSE_ID}"

# ---------------------------------------------------------------------------
# 5. Forgot password
# ---------------------------------------------------------------------------

header "5. Forgot Password Flow"

browse "$FRONTEND/forgot-password" "Opening forgot password page..."

step "POST /forgot-password"
call POST "$IDENTITY/forgot-password" "{\"email\":\"${STUDENT_EMAIL}\"}"

step "Extract reset token from Docker logs"
RESET_TOKEN=$(extract_reset_token)
if [[ -z "$RESET_TOKEN" ]]; then
    echo -e "${R}  Could not extract reset token from logs. Aborting.${N}"
    exit 1
fi
echo -e "  Token: ${B}${RESET_TOKEN}${N}"

browse "$FRONTEND/reset-password?token=${RESET_TOKEN}" "Opening reset password page..."

step "POST /reset-password"
call POST "$IDENTITY/reset-password" "{\"token\":\"${RESET_TOKEN}\",\"new_password\":\"newdemo123\"}"

step "POST /login with new password"
call POST "$IDENTITY/login" "{\"email\":\"${STUDENT_EMAIL}\",\"password\":\"newdemo123\"}"
STUDENT_TOKEN=$(jq_field '.access_token')
STUDENT_REFRESH=$(jq_field '.refresh_token')

# ---------------------------------------------------------------------------
# 6. Token refresh + logout
# ---------------------------------------------------------------------------

header "6. Token Refresh + Logout"

step "POST /refresh"
call POST "$IDENTITY/refresh" "{\"refresh_token\":\"${STUDENT_REFRESH}\"}"
STUDENT_TOKEN=$(jq_field '.access_token')
STUDENT_REFRESH=$(jq_field '.refresh_token')

step "POST /logout"
call POST "$IDENTITY/logout" "{\"refresh_token\":\"${STUDENT_REFRESH}\"}"

# ---------------------------------------------------------------------------
# 7. Catalog filters (bonus)
# ---------------------------------------------------------------------------

header "7. Catalog with Filters"

browse "$FRONTEND/courses?sort_by=avg_rating" "Opening catalog — sorted by rating..."

step "GET /courses — top rated"
call GET "$COURSE/courses?sort_by=avg_rating&limit=3"

browse "$FRONTEND/courses?q=Demo" "Opening catalog — search 'Demo'..."

step "GET /courses — search by keyword"
call GET "$COURSE/courses?q=Demo&limit=5"

step "GET /courses — filter by category + level"
call GET "$COURSE/courses?category_id=${CATEGORY_ID}&level=beginner&limit=5"

browse "$FRONTEND/notifications" "Opening notifications page..."

# ---------------------------------------------------------------------------
# 8. AI-Powered Learning (AI service + browser)
# ---------------------------------------------------------------------------

header "8. AI-Powered Learning"

step "Re-login student (was logged out in section 6)"
call POST "$IDENTITY/login" "{\"email\":\"${STUDENT_EMAIL}\",\"password\":\"newdemo123\"}"
STUDENT_TOKEN=$(jq_field '.access_token')

LESSON_CONTENT="Python is a high-level, interpreted programming language created by Guido van Rossum. It supports multiple programming paradigms including procedural, object-oriented, and functional programming. Key features include dynamic typing, automatic memory management via garbage collection, and a comprehensive standard library. Python uses indentation to define code blocks instead of curly braces. Variables do not need explicit type declarations. Common data structures include lists (ordered, mutable), tuples (ordered, immutable), dictionaries (key-value pairs), and sets (unordered, unique elements). Python supports list comprehensions for concise iteration and filtering. Exception handling uses try/except/finally blocks. Functions are first-class objects and can be passed as arguments."

step "POST /ai/quiz/generate — AI generates quiz from lesson content"
call POST "$AI/ai/quiz/generate" \
    "{\"lesson_id\":\"${LESSON1_ID}\",\"content\":\"${LESSON_CONTENT}\"}" \
    "$STUDENT_TOKEN"
echo -e "  ${G}AI generated quiz with $(echo "$LAST_BODY" | jq '.questions | length') questions${N}"

step "POST /ai/summary/generate — AI summarizes lesson"
call POST "$AI/ai/summary/generate" \
    "{\"lesson_id\":\"${LESSON1_ID}\",\"content\":\"${LESSON_CONTENT}\"}" \
    "$STUDENT_TOKEN"
echo -e "  ${G}Summary preview: $(echo "$LAST_BODY" | jq -r '.summary' | head -c 120)...${N}"

step "POST /ai/tutor/chat — start Socratic tutoring session"
call POST "$AI/ai/tutor/chat" \
    "{\"lesson_id\":\"${LESSON1_ID}\",\"message\":\"What is the difference between a list and a tuple in Python?\",\"lesson_content\":\"${LESSON_CONTENT}\"}" \
    "$STUDENT_TOKEN"
SESSION_ID=$(jq_field '.session_id')
CREDITS=$(jq_field '.credits_remaining')
echo -e "  ${G}Tutor session: ${SESSION_ID}, credits remaining: ${CREDITS}${N}"

step "POST /ai/tutor/chat — follow-up question (multi-turn)"
call POST "$AI/ai/tutor/chat" \
    "{\"lesson_id\":\"${LESSON1_ID}\",\"message\":\"So tuples are faster because they are immutable?\",\"lesson_content\":\"${LESSON_CONTENT}\",\"session_id\":\"${SESSION_ID}\"}" \
    "$STUDENT_TOKEN"
echo -e "  ${G}Credits remaining: $(jq_field '.credits_remaining')${N}"

step "POST /ai/tutor/feedback — rate tutor response"
call POST "$AI/ai/tutor/feedback" \
    "{\"session_id\":\"${SESSION_ID}\",\"message_index\":0,\"rating\":1}" \
    "$STUDENT_TOKEN"

browse "$FRONTEND/courses/${COURSE_ID}/lessons/${LESSON1_ID}" "Opening lesson page — AI features visible..."

# ---------------------------------------------------------------------------
# 9. Quizzes & Knowledge Graph (Learning service)
# ---------------------------------------------------------------------------

header "9. Quizzes & Knowledge Graph"

step "Teacher: POST /quizzes — create quiz for lesson 1"
call POST "$LEARNING/quizzes" \
    "{\"lesson_id\":\"${LESSON1_ID}\",\"course_id\":\"${COURSE_ID}\",\"questions\":[{\"text\":\"What keyword defines a function in Python?\",\"options\":[\"func\",\"def\",\"function\",\"define\"],\"correct_index\":1,\"explanation\":\"The def keyword is used to define functions in Python.\"},{\"text\":\"Which data structure is immutable?\",\"options\":[\"list\",\"dict\",\"tuple\",\"set\"],\"correct_index\":2,\"explanation\":\"Tuples are immutable ordered sequences.\"},{\"text\":\"How does Python define code blocks?\",\"options\":[\"Curly braces\",\"Parentheses\",\"Indentation\",\"Keywords\"],\"correct_index\":2,\"explanation\":\"Python uses indentation instead of braces.\"}]}" \
    "$TEACHER_TOKEN"
QUIZ_ID=$(jq_field '.id')
echo -e "  ${G}Quiz ID: ${QUIZ_ID}${N}"

step "Teacher: POST /concepts — create 'Python Basics' concept"
call POST "$LEARNING/concepts" \
    "{\"course_id\":\"${COURSE_ID}\",\"lesson_id\":\"${LESSON1_ID}\",\"name\":\"Python Basics\",\"description\":\"Core Python syntax and data types\"}" \
    "$TEACHER_TOKEN"
CONCEPT1_ID=$(jq_field '.id')

step "Teacher: POST /concepts — create 'Data Structures' concept"
call POST "$LEARNING/concepts" \
    "{\"course_id\":\"${COURSE_ID}\",\"lesson_id\":\"${LESSON1_ID}\",\"name\":\"Data Structures\",\"description\":\"Lists, tuples, dicts, and sets\"}" \
    "$TEACHER_TOKEN"
CONCEPT2_ID=$(jq_field '.id')

step "Teacher: POST /concepts/${CONCEPT2_ID}/prerequisites — Data Structures requires Python Basics"
call POST "$LEARNING/concepts/${CONCEPT2_ID}/prerequisites" \
    "{\"prerequisite_id\":\"${CONCEPT1_ID}\"}" \
    "$TEACHER_TOKEN"

step "Student: GET /concepts/course/${COURSE_ID} — view knowledge graph"
call GET "$LEARNING/concepts/course/${COURSE_ID}" "" "$STUDENT_TOKEN"
echo -e "  ${G}Concepts in graph: $(echo "$LAST_BODY" | jq '.concepts | length')${N}"

step "Student: POST /quizzes/${QUIZ_ID}/submit — take the quiz"
call POST "$LEARNING/quizzes/${QUIZ_ID}/submit" \
    '{"answers":[1,2,2]}' \
    "$STUDENT_TOKEN"
QUIZ_SCORE=$(jq_field '.score')
echo -e "  ${G}Quiz score: ${QUIZ_SCORE} ($(jq_field '.correct_count')/$(jq_field '.total_questions') correct)${N}"

step "Student: GET /quizzes/${QUIZ_ID}/attempts/me — view attempt history"
call GET "$LEARNING/quizzes/${QUIZ_ID}/attempts/me" "" "$STUDENT_TOKEN"

step "Student: GET /concepts/mastery/course/${COURSE_ID} — view mastery after quiz"
call GET "$LEARNING/concepts/mastery/course/${COURSE_ID}" "" "$STUDENT_TOKEN"
echo -e "  ${G}Mastery updated from quiz performance${N}"

browse "$FRONTEND/courses/${COURSE_ID}" "Opening course page — quiz results and knowledge graph..."

# ---------------------------------------------------------------------------
# 10. Flashcards & Gamification
# ---------------------------------------------------------------------------

header "10. Flashcards & Gamification"

step "Student: POST /flashcards — create flashcard"
call POST "$LEARNING/flashcards" \
    "{\"course_id\":\"${COURSE_ID}\",\"concept\":\"Python list vs tuple\",\"answer\":\"Lists are mutable and use square brackets. Tuples are immutable and use parentheses.\"}" \
    "$STUDENT_TOKEN"
CARD_ID=$(jq_field '.id')
echo -e "  ${G}Flashcard ID: ${CARD_ID}, due: $(jq_field '.due')${N}"

step "Student: GET /flashcards/due — check due cards"
call GET "$LEARNING/flashcards/due" "" "$STUDENT_TOKEN"
echo -e "  ${G}Due cards: $(jq_field '.total')${N}"

step "Student: POST /flashcards/${CARD_ID}/review — review with 'Good' rating"
call POST "$LEARNING/flashcards/${CARD_ID}/review" \
    '{"rating":3}' \
    "$STUDENT_TOKEN"
echo -e "  ${G}Next review: $(jq_field '.next_due'), stability: $(jq_field '.new_stability')${N}"

step "Student: POST /streaks/activity — record daily activity"
call POST "$LEARNING/streaks/activity" "" "$STUDENT_TOKEN"
echo -e "  ${G}Current streak: $(jq_field '.current_streak') days${N}"

step "Student: POST /leaderboards/courses/${COURSE_ID}/opt-in — join leaderboard"
call POST "$LEARNING/leaderboards/courses/${COURSE_ID}/opt-in" "" "$STUDENT_TOKEN"

step "Student: POST /leaderboards/courses/${COURSE_ID}/score — add quiz score"
call POST "$LEARNING/leaderboards/courses/${COURSE_ID}/score" \
    '{"points":100}' \
    "$STUDENT_TOKEN"

step "Student: GET /leaderboards/courses/${COURSE_ID} — view leaderboard"
call GET "$LEARNING/leaderboards/courses/${COURSE_ID}" "" "$STUDENT_TOKEN"
echo -e "  ${G}Leaderboard entries: $(jq_field '.total')${N}"

step "Student: POST /discussions/comments — comment on lesson"
call POST "$LEARNING/discussions/comments" \
    "{\"lesson_id\":\"${LESSON1_ID}\",\"course_id\":\"${COURSE_ID}\",\"content\":\"Great lesson! The explanation of list comprehensions was very clear.\"}" \
    "$STUDENT_TOKEN"
COMMENT_ID=$(jq_field '.id')

step "Teacher: POST /discussions/comments/${COMMENT_ID}/upvote — upvote student comment"
call POST "$LEARNING/discussions/comments/${COMMENT_ID}/upvote" "" "$TEACHER_TOKEN"
echo -e "  ${G}Upvoted! Count: $(jq_field '.upvote_count')${N}"

step "Student: GET /discussions/lessons/${LESSON1_ID}/comments — view discussion"
call GET "$LEARNING/discussions/lessons/${LESSON1_ID}/comments" "" "$STUDENT_TOKEN"

step "Student: GET /xp/me — check XP earned"
call GET "$LEARNING/xp/me" "" "$STUDENT_TOKEN"
echo -e "  ${G}Total XP: $(jq_field '.total_xp')${N}"

step "Student: GET /badges/me — check unlocked badges"
call GET "$LEARNING/badges/me" "" "$STUDENT_TOKEN"
echo -e "  ${G}Badges earned: $(jq_field '.total')${N}"

browse "$FRONTEND/courses/${COURSE_ID}" "Opening course page — full gamification visible..."

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo -e "${G}======================================================================${N}"
echo -e "${G}  Demo completed successfully!${N}"
echo -e "${G}----------------------------------------------------------------------${N}"
echo -e "${G}  Student:  ${STUDENT_EMAIL}${N}"
echo -e "${G}  Teacher:  ${TEACHER_EMAIL}${N}"
echo -e "${G}  Course:   Demo Course ${TS} (${COURSE_ID})${N}"
echo -e "${G}----------------------------------------------------------------------${N}"
echo -e "${G}  Services demonstrated:${N}"
echo -e "${G}    Identity (8001)     — registration, verification, auth${N}"
echo -e "${G}    Course (8002)       — CRUD, curriculum, reviews, catalog${N}"
echo -e "${G}    Enrollment (8003)   — enroll, progress, auto-completion${N}"
echo -e "${G}    Payment (8004)      — mock payments${N}"
echo -e "${G}    Notification (8005) — notifications${N}"
echo -e "${G}    AI (8006)           — quiz gen, summary, Socratic tutor${N}"
echo -e "${G}    Learning (8007)     — quizzes, flashcards, concepts,${N}"
echo -e "${G}                          streaks, leaderboard, discussions,${N}"
echo -e "${G}                          XP, badges${N}"
echo -e "${G}======================================================================${N}"
echo ""
