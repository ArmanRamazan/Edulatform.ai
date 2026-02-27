import asyncio
import json
import os
import random
import io
import uuid
from datetime import date, datetime, timedelta, timezone

import asyncpg
from faker import Faker

IDENTITY_DB_URL = os.environ["IDENTITY_DB_URL"]
COURSE_DB_URL = os.environ["COURSE_DB_URL"]
ENROLLMENT_DB_URL = os.environ["ENROLLMENT_DB_URL"]
PAYMENT_DB_URL = os.environ["PAYMENT_DB_URL"]
NOTIFICATION_DB_URL = os.environ["NOTIFICATION_DB_URL"]
LEARNING_DB_URL = os.environ["LEARNING_DB_URL"]

USER_COUNT = 50_000
COURSE_COUNT = 100_000
ENROLLMENT_COUNT = 200_000
PAYMENT_COUNT = 50_000
REVIEW_COUNT = 100_000
BATCH_SIZE = 5_000

# Learning seed constants
QUIZ_LESSON_RATIO = 0.5  # 50% of lessons get a quiz
CONCEPTS_PER_COURSE = (3, 6)
QUIZ_ATTEMPT_COUNT = 50_000
FLASHCARD_COUNT = 30_000
STREAK_COUNT = 10_000
COMMENT_COUNT = 20_000

# 80% students, 20% teachers
TEACHER_RATIO = 0.2
# 70% of teachers are verified
TEACHER_VERIFIED_RATIO = 0.7

fake = Faker()
# Pre-hash a single password for all seed users (bcrypt is slow, we don't need unique hashes for testing)
SEED_PASSWORD_HASH = "$2b$12$UATV7vr3iDCYLCAvv2bqquAgxLOUlKmIrXDGcowenuwxvFT0z.7Oa"


async def seed_users(pool: asyncpg.Pool) -> tuple[list[str], list[str], list[str]]:
    print(f"Seeding {USER_COUNT} users...")
    teacher_count = int(USER_COUNT * TEACHER_RATIO)

    for batch_start in range(0, USER_COUNT, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, USER_COUNT)
        buf = io.BytesIO()

        for i in range(batch_start, batch_end):
            is_teacher = i < teacher_count
            role = "teacher" if is_teacher else "student"
            is_verified = "true" if (is_teacher and random.random() < TEACHER_VERIFIED_RATIO) else "false"
            email = f"user{i}@example.com"
            name = fake.name()
            line = f"{email}\t{SEED_PASSWORD_HASH}\t{name}\t{role}\t{is_verified}\n"
            buf.write(line.encode())

        buf.seek(0)

        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "users",
                source=buf,
                columns=["email", "password_hash", "name", "role", "is_verified"],
                format="text",
            )

        print(f"  Users: {batch_end}/{USER_COUNT}")

    # Get teacher IDs (verified only) for course creation
    teacher_rows = await pool.fetch(
        "SELECT id FROM users WHERE role = 'teacher' AND is_verified = true"
    )
    teacher_ids = [str(row["id"]) for row in teacher_rows]

    student_rows = await pool.fetch("SELECT id FROM users WHERE role = 'student'")
    student_ids = [str(row["id"]) for row in student_rows]

    all_rows = await pool.fetch("SELECT id FROM users")
    all_ids = [str(row["id"]) for row in all_rows]

    print(f"Seeded {len(all_ids)} users ({len(teacher_ids)} verified teachers, {len(student_ids)} students)")
    return all_ids, teacher_ids, student_ids


async def seed_courses(pool: asyncpg.Pool, teacher_ids: list[str]) -> list[tuple[str, bool, float]]:
    print(f"Seeding {COURSE_COUNT} courses...")

    subjects = [
        "Python", "JavaScript", "Machine Learning", "Data Science", "Web Development",
        "Mobile Development", "DevOps", "Cloud Computing", "Cybersecurity", "Algorithms",
    ]
    adjectives = [
        "Complete", "Advanced", "Practical", "Modern", "Professional",
        "Beginner-Friendly", "Intensive", "Hands-On", "Comprehensive", "Essential",
    ]
    levels = ["beginner", "intermediate", "advanced"]

    for batch_start in range(0, COURSE_COUNT, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, COURSE_COUNT)
        buf = io.BytesIO()

        for _ in range(batch_start, batch_end):
            teacher_id = random.choice(teacher_ids)
            adj = random.choice(adjectives)
            subj = random.choice(subjects)
            title = f"{adj} {subj}: {fake.bs().title()}"
            description = fake.paragraph(nb_sentences=3)
            is_free = random.random() < 0.3
            price = "\\N" if is_free else str(round(random.uniform(9.99, 199.99), 2))
            duration_minutes = random.choice([30, 60, 90, 120, 180, 240, 360, 480, 600])
            level = random.choice(levels)
            line = f"{teacher_id}\t{title}\t{description}\t{is_free}\t{price}\t{duration_minutes}\t{level}\n"
            buf.write(line.encode())

        buf.seek(0)

        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "courses",
                source=buf,
                columns=["teacher_id", "title", "description", "is_free", "price", "duration_minutes", "level"],
                format="text",
            )

        print(f"  Courses: {batch_end}/{COURSE_COUNT}")

    # Fetch course data for enrollments
    rows = await pool.fetch("SELECT id, is_free, price FROM courses")
    course_data = [(str(r["id"]), r["is_free"], float(r["price"] or 0)) for r in rows]
    print(f"Seeded {COURSE_COUNT} courses")
    return course_data


async def seed_modules_and_lessons(pool: asyncpg.Pool) -> None:
    """Seed modules and lessons for first 10K courses."""
    print("Seeding modules and lessons...")

    course_rows = await pool.fetch(
        "SELECT id FROM courses ORDER BY created_at LIMIT 10000"
    )
    course_ids = [str(r["id"]) for r in course_rows]

    module_titles = [
        "Введение", "Основы", "Продвинутые темы", "Практика", "Итоговый проект",
        "Теория", "Инструменты", "Архитектура",
    ]
    lesson_prefixes = [
        "Что такое", "Как работает", "Настройка", "Практикум:", "Разбор",
        "Основы", "Углублённо:", "Задание:",
    ]
    lesson_topics = [
        "переменные", "функции", "классы", "модули", "тестирование",
        "деплой", "базы данных", "API", "авторизация", "кэширование",
    ]

    total_modules = 0
    total_lessons = 0

    for batch_start in range(0, len(course_ids), 500):
        batch_courses = course_ids[batch_start:batch_start + 500]
        module_buf = io.BytesIO()
        modules_in_batch: list[tuple[str, str, int]] = []  # (module_placeholder, course_id, order)

        for course_id in batch_courses:
            num_modules = random.randint(3, 5)
            chosen_titles = random.sample(module_titles, min(num_modules, len(module_titles)))
            for order, mtitle in enumerate(chosen_titles):
                line = f"{course_id}\t{mtitle}\t{order}\n"
                module_buf.write(line.encode())
                total_modules += 1

        module_buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "modules", source=module_buf,
                columns=["course_id", "title", "order"], format="text",
            )

        # Now fetch these modules and seed lessons
        module_rows = await pool.fetch(
            'SELECT id, course_id FROM modules WHERE course_id = ANY($1::uuid[]) ORDER BY "order"',
            [r["id"] for r in course_rows[batch_start:batch_start + 500]],
        )

        lesson_buf = io.BytesIO()
        for mod_row in module_rows:
            num_lessons = random.randint(3, 8)
            for order in range(num_lessons):
                prefix = random.choice(lesson_prefixes)
                topic = random.choice(lesson_topics)
                ltitle = f"{prefix} {topic}"
                content = fake.paragraph(nb_sentences=5)
                duration = random.choice([10, 15, 20, 25, 30, 45, 60])
                line = f"{mod_row['id']}\t{ltitle}\t{content}\t\\N\t{duration}\t{order}\n"
                lesson_buf.write(line.encode())
                total_lessons += 1

        lesson_buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "lessons", source=lesson_buf,
                columns=["module_id", "title", "content", "video_url", "duration_minutes", "order"],
                format="text",
            )

        print(f"  Modules+Lessons: {min(batch_start + 500, len(course_ids))}/{len(course_ids)} courses")

    print(f"Seeded {total_modules} modules, {total_lessons} lessons")


async def seed_reviews(pool: asyncpg.Pool, student_ids: list[str]) -> None:
    """Seed reviews for courses."""
    print(f"Seeding ~{REVIEW_COUNT} reviews...")

    course_rows = await pool.fetch("SELECT id FROM courses")
    course_ids = [str(r["id"]) for r in course_rows]

    seen: set[tuple[str, str]] = set()
    written = 0

    for batch_start in range(0, REVIEW_COUNT, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, REVIEW_COUNT)
        buf = io.BytesIO()
        batch_written = 0

        for _ in range(batch_start, batch_end):
            student_id = random.choice(student_ids)
            course_id = random.choice(course_ids)
            key = (student_id, course_id)
            if key in seen:
                continue
            seen.add(key)

            rating = random.choices([1, 2, 3, 4, 5], weights=[5, 5, 15, 35, 40])[0]
            comment = fake.sentence() if random.random() < 0.7 else ""
            line = f"{student_id}\t{course_id}\t{rating}\t{comment}\n"
            buf.write(line.encode())
            batch_written += 1

        if batch_written == 0:
            continue

        buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "reviews", source=buf,
                columns=["student_id", "course_id", "rating", "comment"],
                format="text",
            )
        written += batch_written
        print(f"  Reviews: {written}/{REVIEW_COUNT}")

    # Update avg_rating and review_count on courses
    await pool.execute("""
        UPDATE courses c SET
            avg_rating = sub.avg_rating,
            review_count = sub.cnt
        FROM (
            SELECT course_id, AVG(rating)::NUMERIC(3,2) as avg_rating, count(*) as cnt
            FROM reviews GROUP BY course_id
        ) sub
        WHERE c.id = sub.course_id
    """)

    print(f"Seeded {written} reviews, updated course ratings")


async def seed_payments(
    pool: asyncpg.Pool,
    student_ids: list[str],
    paid_courses: list[tuple[str, float]],
) -> list[tuple[str, str, str]]:
    """Seed payments and return (payment_id, student_id, course_id) tuples."""
    print(f"Seeding {PAYMENT_COUNT} payments...")

    payment_records: list[tuple[str, str, str]] = []

    for batch_start in range(0, PAYMENT_COUNT, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, PAYMENT_COUNT)
        buf = io.BytesIO()

        for _ in range(batch_start, batch_end):
            student_id = random.choice(student_ids)
            course_id, price = random.choice(paid_courses)
            line = f"{student_id}\t{course_id}\t{price}\tcompleted\n"
            buf.write(line.encode())

        buf.seek(0)

        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "payments",
                source=buf,
                columns=["student_id", "course_id", "amount", "status"],
                format="text",
            )

        print(f"  Payments: {batch_end}/{PAYMENT_COUNT}")

    rows = await pool.fetch("SELECT id, student_id, course_id FROM payments")
    payment_records = [(str(r["id"]), str(r["student_id"]), str(r["course_id"])) for r in rows]
    print(f"Seeded {len(payment_records)} payments")
    return payment_records


async def seed_enrollments(
    pool: asyncpg.Pool,
    student_ids: list[str],
    course_data: list[tuple[str, bool, float]],
    payment_records: list[tuple[str, str, str]],
) -> None:
    print(f"Seeding {ENROLLMENT_COUNT} enrollments...")

    # Build payment lookup: (student_id, course_id) -> payment_id
    payment_lookup: dict[tuple[str, str], str] = {}
    for pid, sid, cid in payment_records:
        payment_lookup[(sid, cid)] = pid

    seen: set[tuple[str, str]] = set()
    free_course_ids = [cid for cid, is_free, _ in course_data if is_free]
    paid_course_ids = [cid for cid, is_free, _ in course_data if not is_free]

    for batch_start in range(0, ENROLLMENT_COUNT, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, ENROLLMENT_COUNT)
        buf = io.BytesIO()
        written = 0

        for _ in range(batch_start, batch_end):
            student_id = random.choice(student_ids)
            # 60% free, 40% paid
            if random.random() < 0.6 and free_course_ids:
                course_id = random.choice(free_course_ids)
                payment_id = "\\N"
            elif paid_course_ids:
                course_id = random.choice(paid_course_ids)
                payment_id = payment_lookup.get((student_id, course_id), "\\N")
            else:
                course_id = random.choice(free_course_ids)
                payment_id = "\\N"

            key = (student_id, course_id)
            if key in seen:
                continue
            seen.add(key)

            line = f"{student_id}\t{course_id}\t{payment_id}\tenrolled\n"
            buf.write(line.encode())
            written += 1

        if written == 0:
            continue

        buf.seek(0)

        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "enrollments",
                source=buf,
                columns=["student_id", "course_id", "payment_id", "status"],
                format="text",
            )

        print(f"  Enrollments: {min(batch_end, len(seen))}/{ENROLLMENT_COUNT}")

    print(f"Seeded {len(seen)} enrollments")


CONCEPT_NAMES_BY_SUBJECT = {
    "Python": ["Variables", "Functions", "Classes", "Modules", "Decorators", "Generators", "List Comprehensions", "Error Handling"],
    "JavaScript": ["Variables", "Functions", "Closures", "Promises", "Async/Await", "DOM", "Event Loop", "Prototypes"],
    "Machine Learning": ["Linear Regression", "Classification", "Neural Networks", "Gradient Descent", "Overfitting", "Feature Engineering", "Cross-Validation", "Ensemble Methods"],
    "Data Science": ["Pandas", "NumPy", "Visualization", "Statistics", "Data Cleaning", "Hypothesis Testing", "Correlation", "Sampling"],
    "Web Development": ["HTML Basics", "CSS Layout", "Responsive Design", "HTTP Protocol", "REST API", "Authentication", "Caching", "Performance"],
    "Mobile Development": ["Layouts", "Navigation", "State Management", "API Integration", "Local Storage", "Push Notifications", "Gestures", "Animations"],
    "DevOps": ["CI/CD", "Docker", "Kubernetes", "Monitoring", "Logging", "Infrastructure as Code", "Load Balancing", "Security"],
    "Cloud Computing": ["Virtual Machines", "Containers", "Serverless", "Storage", "Networking", "IAM", "Auto-scaling", "CDN"],
    "Cybersecurity": ["Encryption", "Authentication", "SQL Injection", "XSS", "CSRF", "Firewalls", "Penetration Testing", "Incident Response"],
    "Algorithms": ["Big O", "Sorting", "Searching", "Recursion", "Dynamic Programming", "Graphs", "Trees", "Hash Tables"],
}

QUESTION_TEMPLATES = [
    ("What is the primary purpose of {concept}?", ["To {a}", "To {b}", "To {c}", "To {d}"]),
    ("Which statement about {concept} is correct?", ["{concept} is used for {a}", "{concept} requires {b}", "{concept} prevents {c}", "{concept} enables {d}"]),
    ("What is a key benefit of {concept}?", ["Improved {a}", "Better {b}", "Enhanced {c}", "Simplified {d}"]),
    ("When should you use {concept}?", ["When you need {a}", "When you want {b}", "When dealing with {c}", "When optimizing {d}"]),
]

BENEFITS = ["performance", "security", "readability", "scalability", "maintainability", "reliability", "efficiency", "flexibility"]

COMMENT_TEMPLATES = [
    "Great explanation of this topic! Very helpful.",
    "I had trouble understanding this at first, but it makes sense now.",
    "Could someone explain the difference between this and the previous lesson?",
    "This is really useful for real-world applications.",
    "I think there might be a simpler way to approach this.",
    "Thanks for the clear examples!",
    "This concept took me a while to grasp but the practice exercises helped.",
    "How does this relate to what we learned in the earlier modules?",
    "Excellent content, well structured and easy to follow.",
    "I found this lesson particularly challenging but rewarding.",
]


def _generate_question(concept_name: str, order: int) -> tuple[str, str, int, str, int]:
    """Generate a quiz question for a concept. Returns (text, options_json, correct_index, explanation, order)."""
    template_text, template_opts = random.choice(QUESTION_TEMPLATES)
    benefits = random.sample(BENEFITS, 4)
    text = template_text.format(concept=concept_name)
    options = [t.format(a=benefits[0], b=benefits[1], c=benefits[2], d=benefits[3]) for t in template_opts]
    correct_index = random.randint(0, 3)
    explanation = f"The correct answer relates to {concept_name} and {benefits[correct_index]}."
    return text, json.dumps(options), correct_index, explanation, order


async def seed_quizzes_and_questions(
    pool: asyncpg.Pool,
    lesson_data: list[tuple[str, str, str]],
) -> dict[str, list[str]]:
    """Seed quizzes and questions. Returns {quiz_id: [question_ids]} for later use."""
    selected = [ld for ld in lesson_data if random.random() < QUIZ_LESSON_RATIO]
    print(f"Seeding {len(selected)} quizzes...")

    quiz_map: dict[str, list[str]] = {}
    # We need concept names per course for question generation
    course_subjects: dict[str, str] = {}
    subjects = list(CONCEPT_NAMES_BY_SUBJECT.keys())

    for batch_start in range(0, len(selected), BATCH_SIZE):
        batch = selected[batch_start:batch_start + BATCH_SIZE]
        quiz_buf = io.BytesIO()
        question_buf = io.BytesIO()
        batch_quiz_ids: list[str] = []

        for lesson_id, course_id, teacher_id in batch:
            quiz_id = str(uuid.uuid4())
            batch_quiz_ids.append(quiz_id)
            quiz_buf.write(f"{quiz_id}\t{lesson_id}\t{course_id}\t{teacher_id}\n".encode())

            # Assign a subject to the course for generating relevant questions
            if course_id not in course_subjects:
                course_subjects[course_id] = random.choice(subjects)
            subj = course_subjects[course_id]
            concept_names = CONCEPT_NAMES_BY_SUBJECT[subj]

            num_questions = random.randint(3, 4)
            q_ids = []
            for q_order in range(num_questions):
                q_id = str(uuid.uuid4())
                q_ids.append(q_id)
                concept = random.choice(concept_names)
                text, options_json, correct_idx, explanation, _ = _generate_question(concept, q_order)
                # Escape tabs and newlines in text fields for COPY format
                text_safe = text.replace("\t", " ").replace("\n", " ")
                explanation_safe = explanation.replace("\t", " ").replace("\n", " ")
                question_buf.write(
                    f"{q_id}\t{quiz_id}\t{text_safe}\t{options_json}\t{correct_idx}\t{explanation_safe}\t{q_order}\n".encode()
                )
            quiz_map[quiz_id] = q_ids

        quiz_buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "quizzes", source=quiz_buf,
                columns=["id", "lesson_id", "course_id", "teacher_id"], format="text",
            )

        question_buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "questions", source=question_buf,
                columns=["id", "quiz_id", "text", "options", "correct_index", "explanation", "order"],
                format="text",
            )

        print(f"  Quizzes: {min(batch_start + BATCH_SIZE, len(selected))}/{len(selected)}")

    print(f"Seeded {len(quiz_map)} quizzes")
    return quiz_map


async def seed_concepts(
    pool: asyncpg.Pool,
    course_lessons: dict[str, list[tuple[str, str]]],
) -> dict[str, list[tuple[str, str]]]:
    """Seed concepts per course. Returns {course_id: [(concept_id, concept_name)]}."""
    print(f"Seeding concepts for {len(course_lessons)} courses...")
    subjects = list(CONCEPT_NAMES_BY_SUBJECT.keys())
    concept_map: dict[str, list[tuple[str, str]]] = {}
    all_concepts: list[tuple[str, str, str | None, str, str, int]] = []  # (id, course_id, lesson_id, name, desc, order)

    for course_id, lessons in course_lessons.items():
        subj = random.choice(subjects)
        num_concepts = random.randint(*CONCEPTS_PER_COURSE)
        names = random.sample(CONCEPT_NAMES_BY_SUBJECT[subj], min(num_concepts, len(CONCEPT_NAMES_BY_SUBJECT[subj])))
        course_concept_ids = []

        for order, name in enumerate(names):
            c_id = str(uuid.uuid4())
            # Link some concepts to lessons
            lesson_id = lessons[order % len(lessons)][0] if lessons else None
            desc = f"Understanding {name} in the context of {subj}"
            all_concepts.append((c_id, course_id, lesson_id, name, desc, order))
            course_concept_ids.append((c_id, name))

        concept_map[course_id] = course_concept_ids

    # Bulk insert concepts
    for batch_start in range(0, len(all_concepts), BATCH_SIZE):
        batch = all_concepts[batch_start:batch_start + BATCH_SIZE]
        buf = io.BytesIO()
        for c_id, course_id, lesson_id, name, desc, order in batch:
            lid = lesson_id if lesson_id else "\\N"
            buf.write(f"{c_id}\t{course_id}\t{lid}\t{name}\t{desc}\t\\N\t{order}\n".encode())

        buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "concepts", source=buf,
                columns=["id", "course_id", "lesson_id", "name", "description", "parent_id", "order"],
                format="text",
            )
        print(f"  Concepts: {min(batch_start + BATCH_SIZE, len(all_concepts))}/{len(all_concepts)}")

    # Add prerequisites (each concept depends on the previous one in the course)
    prereq_buf = io.BytesIO()
    prereq_count = 0
    for course_id, concepts in concept_map.items():
        for i in range(1, len(concepts)):
            prereq_buf.write(f"{concepts[i][0]}\t{concepts[i - 1][0]}\n".encode())
            prereq_count += 1

    if prereq_count > 0:
        prereq_buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "concept_prerequisites", source=prereq_buf,
                columns=["concept_id", "prerequisite_id"], format="text",
            )

    print(f"Seeded {len(all_concepts)} concepts, {prereq_count} prerequisites")
    return concept_map


async def seed_quiz_attempts_and_mastery(
    pool: asyncpg.Pool,
    course_students: dict[str, list[str]],
    quiz_data: list[tuple[str, str, int]],
    concept_map: dict[str, list[tuple[str, str]]],
) -> list[tuple[str, str, float]]:
    """Seed quiz attempts and concept mastery. Returns [(student_id, course_id, score)]."""
    print(f"Seeding ~{QUIZ_ATTEMPT_COUNT} quiz attempts...")
    if not quiz_data:
        print("  No quiz data available, skipping.")
        return []

    attempts: list[tuple[str, str, float]] = []  # (student_id, course_id, score)
    seen: set[tuple[str, str]] = set()
    attempt_buf = io.BytesIO()
    written = 0

    for _ in range(QUIZ_ATTEMPT_COUNT * 2):  # oversample for dedup
        if written >= QUIZ_ATTEMPT_COUNT:
            break
        quiz_id, course_id, num_questions = random.choice(quiz_data)
        students = course_students.get(course_id, [])
        if not students:
            continue
        student_id = random.choice(students)
        key = (student_id, quiz_id)
        if key in seen:
            continue
        seen.add(key)

        # Generate random answers and score
        answers = [random.randint(0, 3) for _ in range(num_questions)]
        # Weighted toward higher scores for demo appeal
        score = random.choices(
            [1.0, 0.75, 0.5, 0.25, 0.0],
            weights=[30, 30, 20, 15, 5],
        )[0]
        answers_json = json.dumps(answers)
        attempt_buf.write(f"{quiz_id}\t{student_id}\t{answers_json}\t{score}\n".encode())
        attempts.append((student_id, course_id, score))
        written += 1

        if written % BATCH_SIZE == 0:
            attempt_buf.seek(0)
            async with pool.acquire() as conn:
                await conn.copy_to_table(
                    "quiz_attempts", source=attempt_buf,
                    columns=["quiz_id", "student_id", "answers", "score"], format="text",
                )
            attempt_buf = io.BytesIO()
            print(f"  Quiz attempts: {written}/{QUIZ_ATTEMPT_COUNT}")

    # Flush remaining
    if attempt_buf.tell() > 0:
        attempt_buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "quiz_attempts", source=attempt_buf,
                columns=["quiz_id", "student_id", "answers", "score"], format="text",
            )

    print(f"Seeded {written} quiz attempts")

    # Seed concept mastery from quiz attempts
    print("Seeding concept mastery...")
    mastery_data: dict[tuple[str, str], float] = {}  # (student_id, concept_id) -> mastery
    for student_id, course_id, score in attempts:
        concepts = concept_map.get(course_id, [])
        for concept_id, _ in concepts:
            key = (student_id, concept_id)
            current = mastery_data.get(key, 0.0)
            mastery_data[key] = min(1.0, current + score * 0.3)

    mastery_items = list(mastery_data.items())
    for batch_start in range(0, len(mastery_items), BATCH_SIZE):
        batch = mastery_items[batch_start:batch_start + BATCH_SIZE]
        buf = io.BytesIO()
        for (student_id, concept_id), mastery in batch:
            buf.write(f"{student_id}\t{concept_id}\t{mastery}\n".encode())
        buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "concept_mastery", source=buf,
                columns=["student_id", "concept_id", "mastery"], format="text",
            )

    print(f"Seeded {len(mastery_items)} concept mastery records")
    return attempts


async def seed_flashcards(
    pool: asyncpg.Pool,
    concept_map: dict[str, list[tuple[str, str]]],
    course_students: dict[str, list[str]],
) -> None:
    """Seed flashcards for students based on course concepts."""
    print(f"Seeding ~{FLASHCARD_COUNT} flashcards...")
    now = datetime.now(timezone.utc).isoformat()
    written = 0
    buf = io.BytesIO()

    courses_with_concepts = [(cid, concepts) for cid, concepts in concept_map.items() if concepts]
    if not courses_with_concepts:
        print("  No concepts available, skipping.")
        return

    for _ in range(FLASHCARD_COUNT * 2):
        if written >= FLASHCARD_COUNT:
            break
        course_id, concepts = random.choice(courses_with_concepts)
        students = course_students.get(course_id, [])
        if not students:
            continue
        student_id = random.choice(students)
        concept_id, concept_name = random.choice(concepts)

        answer = f"{concept_name} is a fundamental concept that involves understanding its core principles and applications."
        # FSRS initial state: new card
        state = random.choices([0, 1, 2], weights=[40, 30, 30])[0]
        stability = round(random.uniform(0.0, 5.0), 2) if state > 0 else 0.0
        difficulty = round(random.uniform(0.0, 1.0), 2) if state > 0 else 0.0
        reps = random.randint(0, 5) if state > 0 else 0
        lapses = random.randint(0, 2) if state == 3 else 0
        due_offset = random.randint(-3, 7)
        due = (datetime.now(timezone.utc) + timedelta(days=due_offset)).isoformat()
        last_review = (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 14))).isoformat() if state > 0 else "\\N"

        buf.write(
            f"{student_id}\t{course_id}\t{concept_name}\t{answer}\tmanual\t\\N\t"
            f"{stability}\t{difficulty}\t{due}\t{last_review}\t{reps}\t{lapses}\t{state}\n".encode()
        )
        written += 1

        if written % BATCH_SIZE == 0:
            buf.seek(0)
            async with pool.acquire() as conn:
                await conn.copy_to_table(
                    "flashcards", source=buf,
                    columns=["student_id", "course_id", "concept", "answer", "source_type",
                             "source_id", "stability", "difficulty", "due", "last_review",
                             "reps", "lapses", "state"],
                    format="text",
                )
            buf = io.BytesIO()
            print(f"  Flashcards: {written}/{FLASHCARD_COUNT}")

    if buf.tell() > 0:
        buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "flashcards", source=buf,
                columns=["student_id", "course_id", "concept", "answer", "source_type",
                         "source_id", "stability", "difficulty", "due", "last_review",
                         "reps", "lapses", "state"],
                format="text",
            )

    print(f"Seeded {written} flashcards")

    # Seed review_logs for flashcards that have been reviewed (state > 0)
    print("Seeding review logs for flashcards...")
    reviewed_rows = await pool.fetch(
        "SELECT id, state FROM flashcards WHERE state > 0"
    )
    log_buf = io.BytesIO()
    log_count = 0
    for row in reviewed_rows:
        card_id = str(row["id"])
        # 1-3 reviews per card depending on state
        num_reviews = min(row["state"] + 1, 3)
        for _ in range(num_reviews):
            rating = random.choices([1, 2, 3, 4], weights=[10, 20, 40, 30])[0]
            duration_ms = random.randint(2000, 15000)
            days_ago = random.randint(1, 14)
            reviewed_at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
            log_buf.write(f"{card_id}\t{rating}\t{duration_ms}\t{reviewed_at}\n".encode())
            log_count += 1

        if log_count % BATCH_SIZE == 0 and log_count > 0:
            log_buf.seek(0)
            async with pool.acquire() as conn:
                await conn.copy_to_table(
                    "review_logs", source=log_buf,
                    columns=["card_id", "rating", "review_duration_ms", "reviewed_at"],
                    format="text",
                )
            log_buf = io.BytesIO()
            print(f"  Review logs: {log_count}")

    if log_buf.tell() > 0:
        log_buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "review_logs", source=log_buf,
                columns=["card_id", "rating", "review_duration_ms", "reviewed_at"],
                format="text",
            )

    print(f"Seeded {log_count} review logs")


async def seed_xp_and_badges(
    pool: asyncpg.Pool,
    student_ids: list[str],
    quiz_attempts: list[tuple[str, str, float]],
    enrollment_data: list[tuple[str, str]],
) -> None:
    """Seed XP events and badges."""
    print("Seeding XP events...")
    xp_rewards = {"lesson_complete": 10, "quiz_submit": 20, "flashcard_review": 5}
    actions = list(xp_rewards.keys())
    weights = [40, 35, 25]

    # Build student -> enrolled courses map for realistic course_ids
    student_courses: dict[str, list[str]] = {}
    for sid, cid in enrollment_data:
        student_courses.setdefault(sid, []).append(cid)

    buf = io.BytesIO()
    user_xp: dict[str, int] = {}
    xp_count = min(len(student_ids) * 5, 100_000)

    for i in range(xp_count):
        student_id = random.choice(student_ids)
        action = random.choices(actions, weights=weights)[0]
        points = xp_rewards[action]
        courses = student_courses.get(student_id)
        course_id = random.choice(courses) if courses else "\\N"
        buf.write(f"{student_id}\t{action}\t{points}\t{course_id}\n".encode())
        user_xp[student_id] = user_xp.get(student_id, 0) + points

        if (i + 1) % BATCH_SIZE == 0:
            buf.seek(0)
            async with pool.acquire() as conn:
                await conn.copy_to_table(
                    "xp_events", source=buf,
                    columns=["user_id", "action", "points", "course_id"], format="text",
                )
            buf = io.BytesIO()
            print(f"  XP events: {i + 1}/{xp_count}")

    if buf.tell() > 0:
        buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "xp_events", source=buf,
                columns=["user_id", "action", "points", "course_id"], format="text",
            )

    print(f"Seeded {xp_count} XP events")

    # Seed badges
    print("Seeding badges...")
    badge_buf = io.BytesIO()
    badge_count = 0
    seen_badges: set[tuple[str, str]] = set()

    # first_enrollment for ~30% of students
    for sid in random.sample(student_ids, min(len(student_ids) // 3, 10_000)):
        key = (sid, "first_enrollment")
        if key not in seen_badges:
            seen_badges.add(key)
            badge_buf.write(f"{sid}\tfirst_enrollment\n".encode())
            badge_count += 1

    # quiz_ace for students who scored 1.0
    ace_students = {sid for sid, _, score in quiz_attempts if score >= 1.0}
    for sid in ace_students:
        key = (sid, "quiz_ace")
        if key not in seen_badges:
            seen_badges.add(key)
            badge_buf.write(f"{sid}\tquiz_ace\n".encode())
            badge_count += 1

    # streak_7 for ~10% of students
    for sid in random.sample(student_ids, min(len(student_ids) // 10, 4_000)):
        key = (sid, "streak_7")
        if key not in seen_badges:
            seen_badges.add(key)
            badge_buf.write(f"{sid}\tstreak_7\n".encode())
            badge_count += 1

    # mastery_100 for students who achieved full mastery on any concept
    mastery_rows = await pool.fetch(
        "SELECT DISTINCT student_id FROM concept_mastery WHERE mastery >= 1.0"
    )
    for row in mastery_rows:
        sid = str(row["student_id"])
        key = (sid, "mastery_100")
        if key not in seen_badges:
            seen_badges.add(key)
            badge_buf.write(f"{sid}\tmastery_100\n".encode())
            badge_count += 1

    if badge_count > 0:
        badge_buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "badges", source=badge_buf,
                columns=["user_id", "badge_type"], format="text",
            )

    print(f"Seeded {badge_count} badges")


async def seed_streaks(pool: asyncpg.Pool, student_ids: list[str]) -> None:
    """Seed streak data for students."""
    count = min(STREAK_COUNT, len(student_ids))
    print(f"Seeding {count} streaks...")
    sample = random.sample(student_ids, count)
    today = date.today()

    buf = io.BytesIO()
    for i, student_id in enumerate(sample):
        current_streak = random.choices(
            [1, 2, 3, 5, 7, 10, 14, 21, 30],
            weights=[20, 15, 15, 15, 10, 10, 8, 5, 2],
        )[0]
        longest_streak = max(current_streak, random.randint(current_streak, current_streak + 10))
        # Most streaks are recent (active today or yesterday)
        days_ago = random.choices([0, 1, 2, 3], weights=[50, 30, 10, 10])[0]
        last_activity = today - timedelta(days=days_ago)
        # If streak is broken (days_ago > 1), reset current to 0 conceptually
        if days_ago > 1:
            current_streak = 1
        buf.write(f"{student_id}\t{current_streak}\t{longest_streak}\t{last_activity}\n".encode())

        if (i + 1) % BATCH_SIZE == 0:
            buf.seek(0)
            async with pool.acquire() as conn:
                await conn.copy_to_table(
                    "streaks", source=buf,
                    columns=["user_id", "current_streak", "longest_streak", "last_activity_date"],
                    format="text",
                )
            buf = io.BytesIO()

    if buf.tell() > 0:
        buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "streaks", source=buf,
                columns=["user_id", "current_streak", "longest_streak", "last_activity_date"],
                format="text",
            )

    print(f"Seeded {count} streaks")


async def seed_leaderboard(
    pool: asyncpg.Pool,
    enrollment_data: list[tuple[str, str]],
) -> None:
    """Seed leaderboard entries for enrolled students."""
    # Sample enrollments for leaderboard
    sample_size = min(50_000, len(enrollment_data))
    sample = random.sample(enrollment_data, sample_size)
    print(f"Seeding {sample_size} leaderboard entries...")

    seen: set[tuple[str, str]] = set()
    buf = io.BytesIO()
    written = 0

    for student_id, course_id in sample:
        key = (student_id, course_id)
        if key in seen:
            continue
        seen.add(key)

        score = random.choices(
            [0, 10, 25, 50, 100, 200, 500],
            weights=[10, 20, 25, 20, 15, 7, 3],
        )[0]
        opted_in = "true" if random.random() < 0.85 else "false"
        buf.write(f"{student_id}\t{course_id}\t{score}\t{opted_in}\n".encode())
        written += 1

        if written % BATCH_SIZE == 0:
            buf.seek(0)
            async with pool.acquire() as conn:
                await conn.copy_to_table(
                    "leaderboard_entries", source=buf,
                    columns=["student_id", "course_id", "score", "opted_in"], format="text",
                )
            buf = io.BytesIO()
            print(f"  Leaderboard: {written}/{sample_size}")

    if buf.tell() > 0:
        buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "leaderboard_entries", source=buf,
                columns=["student_id", "course_id", "score", "opted_in"], format="text",
            )

    print(f"Seeded {written} leaderboard entries")


async def seed_comments(
    pool: asyncpg.Pool,
    lesson_data: list[tuple[str, str, str]],
    student_ids: list[str],
) -> None:
    """Seed discussion comments on lessons."""
    print(f"Seeding ~{COMMENT_COUNT} comments...")
    buf = io.BytesIO()
    written = 0

    for _ in range(COMMENT_COUNT):
        lesson_id, course_id, _ = random.choice(lesson_data)
        user_id = random.choice(student_ids)
        content = random.choice(COMMENT_TEMPLATES)
        buf.write(f"{lesson_id}\t{course_id}\t{user_id}\t{content}\t\\N\t0\n".encode())
        written += 1

        if written % BATCH_SIZE == 0:
            buf.seek(0)
            async with pool.acquire() as conn:
                await conn.copy_to_table(
                    "comments", source=buf,
                    columns=["lesson_id", "course_id", "user_id", "content", "parent_id", "upvote_count"],
                    format="text",
                )
            buf = io.BytesIO()
            print(f"  Comments: {written}/{COMMENT_COUNT}")

    if buf.tell() > 0:
        buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "comments", source=buf,
                columns=["lesson_id", "course_id", "user_id", "content", "parent_id", "upvote_count"],
                format="text",
            )

    print(f"Seeded {written} comments")


async def seed_learning(
    learning_pool: asyncpg.Pool,
    course_pool: asyncpg.Pool,
    enrollment_pool: asyncpg.Pool,
    student_ids: list[str],
) -> None:
    """Seed all learning service data."""
    # Check if already seeded
    count = await learning_pool.fetchval("SELECT count(*) FROM quizzes")
    if count > 0:
        print(f"Learning data already seeded ({count} quizzes). Skipping.")
        return

    # Fetch lesson data from course DB (lesson_id, course_id, teacher_id)
    print("Fetching lesson data from course DB...")
    lesson_rows = await course_pool.fetch("""
        SELECT l.id as lesson_id, m.course_id, c.teacher_id
        FROM lessons l
        JOIN modules m ON l.module_id = m.id
        JOIN courses c ON m.course_id = c.id
        ORDER BY c.created_at, m."order", l."order"
    """)
    lesson_data = [(str(r["lesson_id"]), str(r["course_id"]), str(r["teacher_id"])) for r in lesson_rows]

    # Group lessons by course
    course_lessons: dict[str, list[tuple[str, str]]] = {}
    for lid, cid, tid in lesson_data:
        course_lessons.setdefault(cid, []).append((lid, tid))

    print(f"Found {len(lesson_data)} lessons across {len(course_lessons)} courses")

    # Fetch enrollment data
    enrollment_rows = await enrollment_pool.fetch("SELECT student_id, course_id FROM enrollments")
    enrollment_data = [(str(r["student_id"]), str(r["course_id"])) for r in enrollment_rows]

    course_students: dict[str, list[str]] = {}
    for sid, cid in enrollment_data:
        course_students.setdefault(cid, []).append(sid)

    print(f"Found {len(enrollment_data)} enrollments")

    # 1. Quizzes + questions
    quiz_map = await seed_quizzes_and_questions(learning_pool, lesson_data)

    # 2. Concepts
    concept_map = await seed_concepts(learning_pool, course_lessons)

    # 3. Quiz attempts + concept mastery
    # Build quiz data: (quiz_id, course_id, num_questions)
    quiz_rows = await learning_pool.fetch("""
        SELECT q.id, q.course_id, count(qu.id) as num_q
        FROM quizzes q JOIN questions qu ON qu.quiz_id = q.id
        GROUP BY q.id, q.course_id
    """)
    quiz_data = [(str(r["id"]), str(r["course_id"]), int(r["num_q"])) for r in quiz_rows]

    quiz_attempts = await seed_quiz_attempts_and_mastery(
        learning_pool, course_students, quiz_data, concept_map,
    )

    # 4. Flashcards
    await seed_flashcards(learning_pool, concept_map, course_students)

    # 5. XP + badges
    await seed_xp_and_badges(learning_pool, student_ids, quiz_attempts, enrollment_data)

    # 6. Streaks
    await seed_streaks(learning_pool, student_ids)

    # 7. Leaderboard
    await seed_leaderboard(learning_pool, enrollment_data)

    # 8. Comments
    await seed_comments(learning_pool, lesson_data, student_ids)

    print("Learning data seeding complete!")


async def main() -> None:
    identity_pool = await asyncpg.create_pool(IDENTITY_DB_URL, min_size=2, max_size=5)
    course_pool = await asyncpg.create_pool(COURSE_DB_URL, min_size=2, max_size=5)
    enrollment_pool = await asyncpg.create_pool(ENROLLMENT_DB_URL, min_size=2, max_size=5)
    payment_pool = await asyncpg.create_pool(PAYMENT_DB_URL, min_size=2, max_size=5)
    learning_pool = await asyncpg.create_pool(LEARNING_DB_URL, min_size=2, max_size=5)

    try:
        # Check if already seeded
        count = await identity_pool.fetchval("SELECT count(*) FROM users")
        if count >= USER_COUNT:
            print(f"Already seeded ({count} users). Checking learning data...")
            # Still try to seed learning data if it's missing
            student_rows = await identity_pool.fetch("SELECT id FROM users WHERE role = 'student'")
            student_ids = [str(row["id"]) for row in student_rows]
            await seed_learning(learning_pool, course_pool, enrollment_pool, student_ids)
            return

        # Insert admin user before bulk COPY
        await identity_pool.execute(
            """
            INSERT INTO users (email, password_hash, name, role, is_verified)
            VALUES ($1, $2, $3, 'admin', true)
            ON CONFLICT (email) DO NOTHING
            """,
            "admin@eduplatform.com",
            SEED_PASSWORD_HASH,
            "Admin",
        )

        all_ids, teacher_ids, student_ids = await seed_users(identity_pool)
        course_data = await seed_courses(course_pool, teacher_ids)
        await seed_modules_and_lessons(course_pool)
        await seed_reviews(course_pool, student_ids)

        paid_courses = [(cid, price) for cid, is_free, price in course_data if not is_free]
        payment_records = await seed_payments(payment_pool, student_ids, paid_courses)
        await seed_enrollments(enrollment_pool, student_ids, course_data, payment_records)

        # Seed learning data
        await seed_learning(learning_pool, course_pool, enrollment_pool, student_ids)

        print("Seeding complete!")
    finally:
        await identity_pool.close()
        await course_pool.close()
        await enrollment_pool.close()
        await payment_pool.close()
        await learning_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
