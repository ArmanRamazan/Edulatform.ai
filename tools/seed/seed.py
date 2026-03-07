import asyncio
import json
import math
import os
import random
import io
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import asyncpg
import bcrypt
from faker import Faker

IDENTITY_DB_URL = os.environ["IDENTITY_DB_URL"]
COURSE_DB_URL = os.environ["COURSE_DB_URL"]
ENROLLMENT_DB_URL = os.environ["ENROLLMENT_DB_URL"]
PAYMENT_DB_URL = os.environ["PAYMENT_DB_URL"]
NOTIFICATION_DB_URL = os.environ["NOTIFICATION_DB_URL"]
LEARNING_DB_URL = os.environ["LEARNING_DB_URL"]
RAG_DB_URL = os.environ["RAG_DB_URL"]

USER_COUNT = 1_000
COURSE_COUNT = 100
ENROLLMENT_COUNT = 500
PAYMENT_COUNT = 500
REVIEW_COUNT = 200
BATCH_SIZE = 5_000

# Learning seed constants
QUIZ_LESSON_RATIO = 0.5  # 50% of lessons get a quiz
CONCEPTS_PER_COURSE = (3, 6)
QUIZ_ATTEMPT_COUNT = 500
FLASHCARD_COUNT = 300
STREAK_COUNT = 200
COMMENT_COUNT = 200

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
        "SELECT id FROM courses ORDER BY created_at LIMIT 100"
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

# Realistic question banks per subject: list of (question, [4 options], correct_index, explanation)
QUESTION_BANK: dict[str, list[tuple[str, list[str], int, str]]] = {
    "Python": [
        ("What is the output of `len([1, [2, 3], 4])`?", ["2", "3", "4", "5"], 1, "The list has three elements: 1, [2, 3], and 4. Nested lists count as one element."),
        ("Which keyword is used to define a generator function in Python?", ["generate", "yield", "return", "async"], 1, "The yield keyword makes a function a generator, producing values lazily one at a time."),
        ("What does `*args` do in a function definition?", ["Unpacks keyword arguments", "Creates a tuple of positional arguments", "Defines default parameters", "Raises a TypeError"], 1, "The *args syntax collects extra positional arguments into a tuple."),
        ("What is the difference between a list and a tuple?", ["Tuples are faster to iterate", "Lists are immutable", "Tuples are immutable", "There is no difference"], 2, "Tuples are immutable sequences. Once created, their elements cannot be changed."),
        ("What does `@staticmethod` decorator do?", ["Makes a method async", "Binds method to the class instance", "Defines a method that does not receive self or cls", "Caches the method result"], 2, "A static method does not receive an implicit first argument (self or cls)."),
        ("Which built-in function returns an iterator of tuples pairing elements from two lists?", ["map()", "filter()", "zip()", "enumerate()"], 2, "zip() pairs elements from multiple iterables into tuples."),
        ("What is a list comprehension?", ["A way to sort a list", "A concise syntax for creating lists from iterables", "A method to flatten nested lists", "A debugging tool"], 1, "List comprehensions provide a compact syntax like [x*2 for x in range(5)]."),
        ("What is the purpose of `__init__` in a Python class?", ["To delete an object", "To initialize object attributes", "To define class methods", "To import modules"], 1, "The __init__ method is called when creating a new instance to set up initial state."),
        ("How do you handle exceptions in Python?", ["if/else blocks", "try/except blocks", "for/while loops", "with statements"], 1, "try/except blocks catch and handle exceptions that occur during execution."),
        ("What does `pip install` do?", ["Compiles Python source code", "Installs Python packages from PyPI", "Creates a virtual environment", "Updates Python itself"], 1, "pip is the package installer that downloads and installs packages from PyPI."),
        ("What is the output of `bool([])`?", ["True", "False", "None", "Error"], 1, "Empty sequences like [], '', and {} are falsy in Python."),
        ("Which module is used for regular expressions in Python?", ["regex", "re", "match", "pattern"], 1, "The re module provides regular expression matching operations."),
    ],
    "JavaScript": [
        ("What is the difference between `==` and `===` in JavaScript?", ["`==` checks type, `===` checks value", "`===` checks type and value, `==` does type coercion", "They are identical", "`===` is slower"], 1, "Triple equals checks both type and value without coercion, while == performs type coercion."),
        ("What does `Array.prototype.map()` return?", ["The original array modified in place", "A new array with transformed elements", "A single accumulated value", "undefined"], 1, "map() creates a new array by applying a function to each element of the original array."),
        ("What is a closure in JavaScript?", ["A way to close browser tabs", "A function that retains access to its outer scope variables", "A method to end a loop", "An error handling mechanism"], 1, "A closure is a function bundled with its lexical environment, retaining access to outer variables."),
        ("What does `async/await` simplify?", ["DOM manipulation", "Working with Promises", "Array operations", "String formatting"], 1, "async/await provides syntactic sugar for working with Promises, making async code look synchronous."),
        ("What is the output of `typeof null`?", ["'null'", "'undefined'", "'object'", "'boolean'"], 2, "This is a well-known JavaScript quirk: typeof null returns 'object' due to a legacy bug."),
        ("What is the event loop responsible for?", ["Rendering the DOM", "Managing asynchronous callbacks and task scheduling", "Compiling JavaScript code", "Garbage collection"], 1, "The event loop processes the callback queue after the call stack is empty, enabling async behavior."),
        ("Which method converts a JSON string to a JavaScript object?", ["JSON.stringify()", "JSON.parse()", "JSON.convert()", "JSON.decode()"], 1, "JSON.parse() deserializes a JSON string into a JavaScript value."),
        ("What does `const` prevent?", ["Reassignment of the variable binding", "Mutation of the assigned object", "Declaration of the variable", "Use in loops"], 0, "const prevents reassignment of the variable itself, but does not make objects immutable."),
        ("What is prototypal inheritance?", ["Classes inheriting from interfaces", "Objects inheriting directly from other objects", "Functions inheriting from classes", "Variables inheriting types"], 1, "In JavaScript, objects can inherit properties directly from other objects via the prototype chain."),
        ("What does `Array.prototype.reduce()` do?", ["Removes elements from an array", "Accumulates array elements into a single value", "Creates a smaller array", "Sorts array elements"], 1, "reduce() applies a function against an accumulator to reduce an array to a single output value."),
        ("What is `NaN` in JavaScript?", ["A string value", "A special numeric value meaning Not-a-Number", "An error type", "A null reference"], 1, "NaN is a numeric value indicating the result of an invalid mathematical operation."),
        ("How do you create a Promise?", ["new Promise(callback)", "new Promise((resolve, reject) => {})", "Promise.new()", "async function()"], 1, "A Promise is constructed with an executor function that receives resolve and reject callbacks."),
    ],
    "Machine Learning": [
        ("What is overfitting?", ["The model performs poorly on training data", "The model memorizes training data and fails on new data", "The model is too simple", "The model trains too slowly"], 1, "Overfitting occurs when a model learns noise in training data, leading to poor generalization."),
        ("What is the purpose of a validation set?", ["To train the model", "To tune hyperparameters and evaluate model selection", "To generate final metrics", "To clean the data"], 1, "The validation set helps tune hyperparameters without biasing the final test evaluation."),
        ("Which algorithm is used for binary classification?", ["Linear Regression", "Logistic Regression", "K-means Clustering", "PCA"], 1, "Logistic Regression predicts probabilities for binary outcomes using a sigmoid function."),
        ("What does gradient descent optimize?", ["Data quality", "The loss function by adjusting model parameters", "Feature selection", "Training speed"], 1, "Gradient descent iteratively adjusts parameters in the direction that minimizes the loss function."),
        ("What is a feature in machine learning?", ["The model output", "An individual measurable property of the data", "The training algorithm", "The loss function"], 1, "Features are the input variables that the model uses to make predictions."),
        ("What is cross-validation?", ["Training on all data at once", "Splitting data into k folds to evaluate model performance", "Validating data types", "Testing on training data"], 1, "K-fold cross-validation trains and evaluates the model k times on different data splits."),
        ("What is the bias-variance tradeoff?", ["Choosing between accuracy and speed", "Balancing underfitting (bias) and overfitting (variance)", "Selecting features vs. samples", "Trading precision for recall"], 1, "High bias means underfitting; high variance means overfitting. Good models balance both."),
        ("What is regularization?", ["Adding more training data", "Adding a penalty term to prevent overfitting", "Normalizing input features", "Removing outliers"], 1, "Regularization (L1/L2) adds a penalty to large weights, discouraging complex models."),
        ("What does a confusion matrix show?", ["Feature correlations", "True positives, false positives, true negatives, false negatives", "Training loss over time", "Hyperparameter values"], 1, "A confusion matrix summarizes classification results by comparing predicted vs. actual labels."),
        ("What is the difference between supervised and unsupervised learning?", ["Supervised uses GPUs, unsupervised does not", "Supervised uses labeled data, unsupervised finds patterns in unlabeled data", "There is no difference", "Unsupervised is always better"], 1, "Supervised learning trains on labeled examples; unsupervised learning discovers structure in unlabeled data."),
    ],
    "Data Science": [
        ("What does `pandas.DataFrame.groupby()` do?", ["Sorts the DataFrame", "Groups rows by column values for aggregation", "Merges two DataFrames", "Reshapes the DataFrame"], 1, "groupby() splits data into groups based on column values, enabling aggregate operations."),
        ("What is the purpose of data normalization?", ["To delete duplicates", "To scale features to a common range", "To increase data size", "To remove missing values"], 1, "Normalization scales features to a similar range (e.g., 0-1) to prevent dominance by large-valued features."),
        ("What is a p-value in hypothesis testing?", ["The probability of the data being correct", "The probability of observing results as extreme as the data under the null hypothesis", "The percentage of correct predictions", "The population parameter"], 1, "A p-value measures how likely the observed data would occur if the null hypothesis were true."),
        ("Which NumPy function creates an array of zeros?", ["np.empty()", "np.zeros()", "np.null()", "np.clear()"], 1, "np.zeros(shape) creates an array filled with zeros of the specified shape."),
        ("What is the difference between correlation and causation?", ["They are the same thing", "Correlation measures association; causation implies one causes the other", "Causation is weaker than correlation", "Correlation requires an experiment"], 1, "Correlation shows two variables move together; causation means one directly affects the other."),
        ("What is a box plot used for?", ["Showing time series", "Displaying the distribution of data through quartiles", "Plotting geographic data", "Creating network graphs"], 1, "Box plots show median, quartiles, and outliers, summarizing data distribution at a glance."),
        ("What does `DataFrame.fillna()` do?", ["Deletes rows with missing data", "Replaces missing values with a specified value", "Finds null values", "Counts missing values"], 1, "fillna() replaces NaN values with a given value, mean, median, or method like forward fill."),
        ("What is the Central Limit Theorem?", ["Large samples are always normal", "The sampling distribution of the mean approaches normal as sample size increases", "All data follows a bell curve", "Variance decreases with more features"], 1, "The CLT states that sample means tend toward a normal distribution regardless of the population shape."),
        ("What type of chart best shows the relationship between two continuous variables?", ["Bar chart", "Scatter plot", "Pie chart", "Histogram"], 1, "Scatter plots reveal patterns, trends, and correlations between two numerical variables."),
        ("What does `pandas.merge()` do?", ["Concatenates DataFrames vertically", "Joins DataFrames on common columns like SQL JOIN", "Sorts DataFrames", "Splits DataFrames into groups"], 1, "merge() combines DataFrames on shared keys, similar to SQL JOINs."),
    ],
    "Web Development": [
        ("What does the HTTP status code 404 mean?", ["Server error", "Resource not found", "Unauthorized", "Success"], 1, "404 means the server cannot find the requested resource at the given URL."),
        ("What is the purpose of a REST API?", ["To style web pages", "To enable communication between client and server using HTTP methods", "To compile JavaScript", "To manage databases directly"], 1, "REST APIs use HTTP methods (GET, POST, PUT, DELETE) for client-server communication."),
        ("What is CORS?", ["A JavaScript framework", "A browser security mechanism for cross-origin requests", "A CSS property", "A database query language"], 1, "CORS (Cross-Origin Resource Sharing) controls which domains can make requests to your server."),
        ("What does CSS `flexbox` solve?", ["Database queries", "One-dimensional layout alignment and distribution", "Server-side rendering", "API authentication"], 1, "Flexbox provides efficient layout, alignment, and space distribution in a single dimension."),
        ("What is the difference between GET and POST requests?", ["GET sends data in the body, POST in the URL", "GET retrieves data, POST submits data", "They are identical", "POST is faster than GET"], 1, "GET requests retrieve resources; POST requests submit data to be processed by the server."),
        ("What is responsive design?", ["Fast-loading pages", "Design that adapts to different screen sizes", "Server-side rendering", "A JavaScript framework"], 1, "Responsive design uses flexible layouts, media queries, and fluid images to adapt to any screen size."),
        ("What does HTTPS provide over HTTP?", ["Faster page loads", "Encrypted communication between client and server", "Better SEO only", "Larger file uploads"], 1, "HTTPS encrypts data in transit using TLS, protecting against eavesdropping and tampering."),
        ("What is a cookie used for in web development?", ["Styling elements", "Storing small data on the client for session management", "Compiling code", "Database backup"], 1, "Cookies store small pieces of data in the browser, commonly used for sessions and preferences."),
        ("What is the DOM?", ["A CSS framework", "The Document Object Model, a tree representation of HTML", "A database", "A server protocol"], 1, "The DOM is a programming interface representing HTML as a tree of objects that JavaScript can manipulate."),
        ("What is caching in web development?", ["Deleting old data", "Storing frequently accessed data for faster retrieval", "Encrypting API responses", "Minifying JavaScript"], 1, "Caching stores copies of data (in browser, CDN, or server memory) to reduce latency and load."),
    ],
    "Mobile Development": [
        ("What is the purpose of a RecyclerView/FlatList?", ["To display a single image", "To efficiently render large scrollable lists", "To handle API calls", "To manage app permissions"], 1, "RecyclerView/FlatList reuses off-screen views to efficiently render long lists with minimal memory."),
        ("What is deep linking in mobile apps?", ["Downloading files", "Opening a specific screen in the app via a URL", "Creating nested navigation", "Database connections"], 1, "Deep links allow URLs to navigate directly to specific content within a mobile app."),
        ("What is the difference between local and remote push notifications?", ["No difference", "Local are scheduled by the app; remote are sent from a server", "Remote are faster", "Local need internet"], 1, "Local notifications are triggered by the app itself; remote notifications originate from a backend server."),
        ("What is state management in mobile development?", ["Managing server databases", "Handling and synchronizing app data across UI components", "Version control", "Memory allocation"], 1, "State management ensures consistent data flow and UI updates across components."),
        ("What is an APK?", ["A programming language", "Android application package for distribution", "An API protocol", "A design tool"], 1, "APK (Android Package Kit) is the file format used to distribute Android applications."),
        ("What is hot reload?", ["Restarting the entire app", "Injecting updated code without losing app state", "Clearing the cache", "Rebuilding the APK"], 1, "Hot reload injects changed code into the running app, preserving the current state for faster iteration."),
        ("What is the purpose of AsyncStorage/SharedPreferences?", ["Network caching", "Persisting key-value data locally on the device", "Managing app permissions", "Handling push notifications"], 1, "AsyncStorage (React Native) and SharedPreferences (Android) store simple key-value pairs locally."),
        ("What is a splash screen?", ["The main app screen", "A brief introductory screen shown while the app loads", "An error screen", "A settings page"], 1, "Splash screens display branding or a loading indicator while the app initializes resources."),
        ("What does offline-first architecture mean?", ["The app never uses the internet", "The app works without connectivity and syncs data when online", "The app caches everything permanently", "The app requires airplane mode"], 1, "Offline-first apps store data locally and synchronize with the server when a network connection is available."),
        ("What is the purpose of app sandboxing?", ["Improving performance", "Isolating app data and processes for security", "Compressing app storage", "Enabling multitasking"], 1, "Sandboxing restricts each app to its own isolated environment, preventing unauthorized access to other apps' data."),
    ],
    "DevOps": [
        ("What is CI/CD?", ["A programming language", "Continuous Integration and Continuous Delivery/Deployment", "A cloud provider", "A testing framework"], 1, "CI/CD automates building, testing, and deploying code changes to production."),
        ("What is a Docker container?", ["A virtual machine", "A lightweight isolated environment for running applications", "A database server", "A code editor"], 1, "Containers package applications with dependencies, running in isolated but lightweight environments."),
        ("What does Kubernetes orchestrate?", ["Source code", "Container deployment, scaling, and management", "Database queries", "Frontend components"], 1, "Kubernetes automates deploying, scaling, and managing containerized applications across clusters."),
        ("What is Infrastructure as Code (IaC)?", ["Writing code inside infrastructure", "Managing infrastructure through declarative configuration files", "A monitoring tool", "A container format"], 1, "IaC tools like Terraform define infrastructure in code, enabling version control and reproducibility."),
        ("What is the purpose of a load balancer?", ["Compressing files", "Distributing incoming traffic across multiple servers", "Managing databases", "Encrypting data"], 1, "Load balancers distribute requests across servers to ensure no single server is overwhelmed."),
        ("What is a rolling deployment?", ["Deploying to all servers at once", "Gradually replacing old instances with new ones", "Rolling back a failed deployment", "Deploying only on weekends"], 1, "Rolling deployments update instances incrementally, reducing downtime and risk during releases."),
        ("What does a reverse proxy do?", ["Blocks all incoming traffic", "Sits in front of backend servers forwarding client requests", "Encrypts database connections", "Monitors CPU usage"], 1, "A reverse proxy (e.g., Nginx) receives client requests and forwards them to appropriate backend servers."),
        ("What is blue-green deployment?", ["Running two environments and switching traffic between them", "Deploying code only at night", "Using two programming languages", "A testing strategy"], 0, "Blue-green deployment maintains two identical environments, switching traffic to the updated one instantly."),
        ("What is the purpose of a health check endpoint?", ["User authentication", "Allowing monitoring systems to verify service availability", "Logging user activity", "Database backup"], 1, "Health check endpoints return the service status, enabling load balancers and monitors to detect failures."),
        ("What is GitOps?", ["Using Git for social networking", "Managing infrastructure and deployments through Git repositories", "A Git GUI tool", "A branching strategy"], 1, "GitOps uses Git as the single source of truth for declarative infrastructure and application delivery."),
    ],
    "Cloud Computing": [
        ("What is serverless computing?", ["Computing without any servers", "A model where the cloud provider manages server infrastructure", "Peer-to-peer computing", "Edge computing"], 1, "Serverless lets developers run code without managing servers; the provider handles scaling and infrastructure."),
        ("What is auto-scaling?", ["Manual server provisioning", "Automatically adjusting compute resources based on demand", "A storage format", "A networking protocol"], 1, "Auto-scaling adds or removes instances based on load metrics to maintain performance and cost efficiency."),
        ("What does a CDN do?", ["Compiles code", "Caches and serves content from geographically distributed servers", "Creates databases", "Manages containers"], 1, "CDNs reduce latency by serving static content from edge locations closer to the user."),
        ("What is IAM in cloud services?", ["An encryption algorithm", "Identity and Access Management for controlling resource access", "A monitoring dashboard", "A storage service"], 1, "IAM defines who (identity) can do what (access) on which cloud resources."),
        ("What is the difference between IaaS, PaaS, and SaaS?", ["They are the same", "IaaS provides infrastructure, PaaS provides platform, SaaS provides software", "Only SaaS is cloud-based", "PaaS is the cheapest"], 1, "IaaS gives raw compute/storage, PaaS adds runtime/tools, SaaS delivers complete applications."),
        ("What is object storage?", ["A file system with directories", "Flat storage that manages data as objects with metadata", "RAM-based caching", "A database type"], 1, "Object storage (e.g., S3) stores data as objects in a flat namespace with rich metadata and HTTP access."),
        ("What is a VPC?", ["Virtual Programming Console", "Virtual Private Cloud — an isolated network segment in the cloud", "A container format", "A monitoring tool"], 1, "A VPC provides a logically isolated section of the cloud where you can launch resources in a defined network."),
        ("What is multi-region deployment?", ["Using multiple programming languages", "Running applications across different geographic cloud regions", "Deploying microservices", "A backup strategy"], 1, "Multi-region deployment distributes workloads across geographies for low latency and disaster recovery."),
        ("What is cloud-native architecture?", ["Running legacy apps in the cloud", "Designing applications specifically to exploit cloud capabilities", "Using only free cloud services", "A migration strategy"], 1, "Cloud-native apps leverage containers, microservices, and dynamic orchestration to maximize cloud benefits."),
        ("What are spot/preemptible instances?", ["Dedicated servers", "Discounted compute instances that can be reclaimed by the provider", "Free-tier instances", "GPU-only machines"], 1, "Spot instances offer significant cost savings but can be interrupted when the provider needs the capacity back."),
    ],
    "Cybersecurity": [
        ("What is SQL injection?", ["A database optimization technique", "An attack that inserts malicious SQL through user input", "A query caching method", "A stored procedure"], 1, "SQL injection exploits unsanitized user input to execute unauthorized SQL commands."),
        ("What does HTTPS encryption protect against?", ["Slow connections", "Eavesdropping and man-in-the-middle attacks", "Server crashes", "Disk failures"], 1, "HTTPS uses TLS to encrypt traffic, preventing interception and modification of data in transit."),
        ("What is multi-factor authentication (MFA)?", ["Using a strong password", "Requiring two or more verification methods to prove identity", "Encrypting passwords", "Rate limiting login attempts"], 1, "MFA combines something you know (password), have (phone), or are (biometrics) for stronger security."),
        ("What is the principle of least privilege?", ["Give everyone admin access", "Grant users only the minimum permissions needed for their role", "Use the simplest password possible", "Disable all security features"], 1, "Least privilege limits access rights to the bare minimum needed, reducing attack surface."),
        ("What is a firewall?", ["A type of malware", "A network security system that monitors and controls traffic", "A password manager", "A backup tool"], 1, "Firewalls filter incoming and outgoing network traffic based on predefined security rules."),
        ("What is a zero-day vulnerability?", ["A bug found on day zero of development", "A previously unknown security flaw with no available patch", "A vulnerability that takes zero days to fix", "An expired security certificate"], 1, "A zero-day is a vulnerability discovered before the vendor has released a fix, leaving systems exposed."),
        ("What is phishing?", ["A network scanning technique", "A social engineering attack that tricks users into revealing sensitive data", "A type of DDoS attack", "A password cracking method"], 1, "Phishing uses fraudulent emails or websites to deceive victims into disclosing credentials or personal information."),
        ("What is the CIA triad in cybersecurity?", ["A government agency model", "Confidentiality, Integrity, and Availability — core security principles", "Certificate, Identity, Authentication", "A risk assessment framework"], 1, "The CIA triad defines three fundamental security goals: keeping data secret, accurate, and accessible."),
        ("What is a VPN?", ["A type of firewall", "An encrypted tunnel that protects data transmitted over public networks", "A virus protection tool", "A password vault"], 1, "A VPN creates an encrypted connection over the internet, hiding your traffic from eavesdroppers."),
        ("What is penetration testing?", ["Testing network speed", "Authorized simulated attacks to identify security weaknesses", "Installing security patches", "Monitoring server performance"], 1, "Penetration testing proactively finds vulnerabilities by simulating real-world attacks in a controlled manner."),
    ],
    "Algorithms": [
        ("What is the time complexity of binary search?", ["O(n)", "O(log n)", "O(n log n)", "O(1)"], 1, "Binary search halves the search space each step, resulting in O(log n) time complexity."),
        ("What data structure uses FIFO ordering?", ["Stack", "Queue", "Heap", "Tree"], 1, "A Queue follows First-In-First-Out: the first element added is the first one removed."),
        ("What is dynamic programming?", ["Writing code dynamically", "Solving problems by breaking them into overlapping subproblems", "Real-time code generation", "Automatic memory management"], 1, "Dynamic programming solves complex problems by caching results of overlapping subproblems."),
        ("What is the worst-case time complexity of quicksort?", ["O(n)", "O(n log n)", "O(n^2)", "O(log n)"], 2, "Quicksort degrades to O(n^2) when the pivot consistently results in unbalanced partitions."),
        ("What is a hash table?", ["A sorted array", "A data structure mapping keys to values using a hash function", "A binary tree", "A linked list"], 1, "Hash tables use hash functions to compute indices, enabling O(1) average-case lookups."),
        ("What is BFS (Breadth-First Search)?", ["Searching the deepest node first", "Exploring all neighbors at the current depth before going deeper", "A sorting algorithm", "A compression technique"], 1, "BFS explores a graph level by level, visiting all neighbors before moving to the next depth."),
        ("What is the space complexity of merge sort?", ["O(1)", "O(log n)", "O(n)", "O(n^2)"], 2, "Merge sort requires O(n) additional space for the temporary arrays used during merging."),
        ("What is a balanced binary search tree?", ["A tree with equal values in all nodes", "A BST where the height difference between subtrees is at most 1", "A tree with only leaf nodes", "A tree with no children"], 1, "Balanced BSTs (like AVL, Red-Black) maintain height balance for O(log n) operations."),
    ],
}

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


def _generate_questions(subject: str, count: int) -> list[tuple[str, str, int, str, int]]:
    """Generate unique quiz questions from the question bank. Returns [(text, options_json, correct_index, explanation, order)]."""
    bank = QUESTION_BANK.get(subject, QUESTION_BANK["Python"])
    selected = random.sample(bank, min(count, len(bank)))
    return [
        (q_text, json.dumps(options), correct_index, explanation, order)
        for order, (q_text, options, correct_index, explanation) in enumerate(selected)
    ]


async def seed_quizzes_and_questions(
    pool: asyncpg.Pool,
    lesson_data: list[tuple[str, str, str]],
) -> dict[str, tuple[list[str], list[int]]]:
    """Seed quizzes and questions. Returns {quiz_id: (question_ids, correct_indices)}."""
    selected = [ld for ld in lesson_data if random.random() < QUIZ_LESSON_RATIO]
    print(f"Seeding {len(selected)} quizzes...")

    quiz_map: dict[str, tuple[list[str], list[int]]] = {}
    course_subjects: dict[str, str] = {}
    subjects = list(CONCEPT_NAMES_BY_SUBJECT.keys())

    for batch_start in range(0, len(selected), BATCH_SIZE):
        batch = selected[batch_start:batch_start + BATCH_SIZE]
        quiz_buf = io.BytesIO()
        question_buf = io.BytesIO()

        for lesson_id, course_id, teacher_id in batch:
            quiz_id = str(uuid.uuid4())
            quiz_buf.write(f"{quiz_id}\t{lesson_id}\t{course_id}\t{teacher_id}\n".encode())

            if course_id not in course_subjects:
                course_subjects[course_id] = random.choice(subjects)
            subj = course_subjects[course_id]

            num_questions = random.randint(3, 5)
            questions = _generate_questions(subj, num_questions)
            q_ids = []
            correct_indices = []
            for text, options_json, correct_idx, explanation, q_order in questions:
                q_id = str(uuid.uuid4())
                q_ids.append(q_id)
                correct_indices.append(correct_idx)
                text_safe = text.replace("\t", " ").replace("\n", " ")
                explanation_safe = explanation.replace("\t", " ").replace("\n", " ")
                question_buf.write(
                    f"{q_id}\t{quiz_id}\t{text_safe}\t{options_json}\t{correct_idx}\t{explanation_safe}\t{q_order}\n".encode()
                )
            quiz_map[quiz_id] = (q_ids, correct_indices)

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
    quiz_data: list[tuple[str, str, list[int]]],
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
        quiz_id, course_id, correct_indices = random.choice(quiz_data)
        students = course_students.get(course_id, [])
        if not students:
            continue
        student_id = random.choice(students)
        key = (student_id, quiz_id)
        if key in seen:
            continue
        seen.add(key)

        # Generate answers that produce a realistic score
        num_q = len(correct_indices)
        num_correct = random.choices(
            list(range(num_q + 1)),
            weights=[5] + [15] * max(num_q - 2, 0) + [30, 30] if num_q >= 2 else [30, 30],
        )[0]
        # Build answer list: first num_correct match, rest are wrong
        indices = list(range(num_q))
        random.shuffle(indices)
        answers = [0] * num_q
        for i, idx in enumerate(indices):
            if i < num_correct:
                answers[idx] = correct_indices[idx]
            else:
                wrong = [x for x in range(4) if x != correct_indices[idx]]
                answers[idx] = random.choice(wrong)
        score = round(num_correct / num_q, 2) if num_q > 0 else 0.0
        answers_json = json.dumps(answers)
        # Spread attempts across last 30 days for realistic timestamps
        days_ago = random.randint(0, 30)
        hours_offset = random.randint(0, 23)
        completed_at = (datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_offset)).isoformat()
        attempt_buf.write(f"{quiz_id}\t{student_id}\t{answers_json}\t{score}\t{completed_at}\n".encode())
        attempts.append((student_id, course_id, score))
        written += 1

        if written % BATCH_SIZE == 0:
            attempt_buf.seek(0)
            async with pool.acquire() as conn:
                await conn.copy_to_table(
                    "quiz_attempts", source=attempt_buf,
                    columns=["quiz_id", "student_id", "answers", "score", "completed_at"], format="text",
                )
            attempt_buf = io.BytesIO()
            print(f"  Quiz attempts: {written}/{QUIZ_ATTEMPT_COUNT}")

    # Flush remaining
    if attempt_buf.tell() > 0:
        attempt_buf.seek(0)
        async with pool.acquire() as conn:
            await conn.copy_to_table(
                "quiz_attempts", source=attempt_buf,
                columns=["quiz_id", "student_id", "answers", "score", "completed_at"], format="text",
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
    xp_count = min(len(student_ids) * 5, 5_000)

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
    for sid in random.sample(student_ids, min(len(student_ids) // 3, 300)):
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
    for sid in random.sample(student_ids, min(len(student_ids) // 10, 100)):
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
    sample_size = min(500, len(enrollment_data))
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
    # Build quiz data: (quiz_id, course_id, correct_indices) from quiz_map + DB
    quiz_course_rows = await learning_pool.fetch("SELECT id, course_id FROM quizzes")
    quiz_course_map = {str(r["id"]): str(r["course_id"]) for r in quiz_course_rows}
    quiz_data = [
        (qid, quiz_course_map[qid], correct_indices)
        for qid, (_q_ids, correct_indices) in quiz_map.items()
        if qid in quiz_course_map
    ]

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


# ---------------------------------------------------------------------------
# Demo B2B organization — fixed UUIDs for predictable cross-script references
# ---------------------------------------------------------------------------

DEMO_USER_ID = "00000000-0000-4000-a000-000000000001"
DEMO_ORG_ID = "00000000-0000-4000-b000-000000000001"

_DEMO_MEMBERS = [
    ("Sarah Kim", "sarah"),
    ("Mike Johnson", "mike"),
    ("Priya Patel", "priya"),
    ("James Wilson", "james"),
    ("Yuki Tanaka", "yuki"),
    ("Carlos Rodriguez", "carlos"),
    ("Emma Davis", "emma"),
    ("Ali Hassan", "ali"),
    ("Lisa Chen", "lisa"),
]

# Deterministic UUIDs so identity-db and learning-db share the same IDs
_DEMO_MEMBER_UUIDS_MAP: dict[str, str] = {
    f"{prefix}@acme.com": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{prefix}@acme.com"))
    for _name, prefix in _DEMO_MEMBERS
}


def _hash_password(password: str) -> str:
    """Hash a password with bcrypt (12 rounds). Returns utf-8 string."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


async def seed_demo_org(identity_pool: asyncpg.Pool, payment_pool: asyncpg.Pool) -> None:
    """Seed Acme Engineering demo B2B org with 10 members. Idempotent."""
    existing = await identity_pool.fetchval(
        "SELECT id FROM users WHERE id = $1",
        DEMO_USER_ID,
    )
    if existing:
        print("Demo org already seeded. Skipping.")
        return

    print("Seeding demo B2B organization (Acme Engineering)...")

    # 1. Demo admin user: Alex Chen / demo@acme.com / demo123
    await identity_pool.execute(
        """
        INSERT INTO users (id, email, password_hash, name, role, is_verified, email_verified)
        VALUES ($1, $2, $3, $4, 'teacher', true, true)
        ON CONFLICT DO NOTHING
        """,
        DEMO_USER_ID,
        "demo@acme.com",
        _hash_password("demo123"),
        "Alex Chen",
    )

    # 2. Organization
    await identity_pool.execute(
        """
        INSERT INTO organizations (id, name, slug)
        VALUES ($1, $2, $3)
        ON CONFLICT DO NOTHING
        """,
        DEMO_ORG_ID,
        "Acme Engineering",
        "acme",
    )

    # 3. Demo user as org admin
    await identity_pool.execute(
        """
        INSERT INTO org_members (organization_id, user_id, role)
        VALUES ($1, $2, 'admin')
        ON CONFLICT (organization_id, user_id) DO NOTHING
        """,
        DEMO_ORG_ID,
        DEMO_USER_ID,
    )

    # 4. Nine team members (students) — use deterministic uuid5 IDs
    #    so identity-db and learning-db agree on member UUIDs
    for name, prefix in _DEMO_MEMBERS:
        email = f"{prefix}@acme.com"
        member_id = _DEMO_MEMBER_UUIDS_MAP[email]
        await identity_pool.execute(
            """
            INSERT INTO users (id, email, password_hash, name, role, is_verified, email_verified)
            VALUES ($1, $2, $3, $4, 'student', true, true)
            ON CONFLICT (id) DO NOTHING
            """,
            member_id,
            email,
            _hash_password(f"{prefix}123"),
            name,
        )
        await identity_pool.execute(
            """
            INSERT INTO org_members (organization_id, user_id, role)
            VALUES ($1, $2, 'member')
            ON CONFLICT (organization_id, user_id) DO NOTHING
            """,
            DEMO_ORG_ID,
            member_id,
        )

    print("  Created 1 admin (Alex Chen) + 9 members")

    # 5. Enterprise subscription in payment DB
    now = datetime.now(timezone.utc)
    await payment_pool.execute(
        """
        INSERT INTO org_subscriptions (
            organization_id, plan_tier, status, current_seats, max_seats, price_cents,
            current_period_start, current_period_end
        )
        VALUES ($1, 'enterprise', 'active', 10, 50, 100000, $2, $3)
        ON CONFLICT (organization_id) DO NOTHING
        """,
        DEMO_ORG_ID,
        now,
        now + timedelta(days=30),
    )

    print("  Created enterprise subscription ($1000/mo, 50 seats)")
    print("Demo org seeding complete!")


# ---------------------------------------------------------------------------
# RAG demo documents — fixed UUIDs for predictable cross-script references
# ---------------------------------------------------------------------------

DEMO_DOC_IDS: dict[str, str] = {
    "python_best_practices": "00000000-0000-4001-c000-000000000001",
    "rust_ownership":        "00000000-0000-4001-c000-000000000002",
    "typescript_patterns":   "00000000-0000-4001-c000-000000000003",
    "system_design":         "00000000-0000-4001-c000-000000000004",
    "api_design_guide":      "00000000-0000-4001-c000-000000000005",
}

_DEMO_DOCS_DIR = Path(__file__).parent / "demo_documents"

_DEMO_DOCS: list[dict] = [
    {"slug": "python_best_practices", "title": "Python Best Practices for Production Systems"},
    {"slug": "rust_ownership",        "title": "Rust Ownership, Borrowing, and Memory Safety"},
    {"slug": "typescript_patterns",   "title": "TypeScript Patterns for Scalable Applications"},
    {"slug": "system_design",         "title": "System Design Fundamentals for Distributed Systems"},
    {"slug": "api_design_guide",      "title": "API Design Guide: Building Developer-Friendly APIs"},
]

_DEMO_CONCEPTS: list[dict] = [
    # Python (10)
    {"name": "type_hints",           "description": "Static type annotations for Python functions and variables using PEP 484 syntax.", "slug": "python_best_practices"},
    {"name": "async_await",          "description": "Python's cooperative concurrency model for non-blocking I/O using asyncio.", "slug": "python_best_practices"},
    {"name": "testing",              "description": "Unit and integration testing patterns in Python with pytest and AsyncMock.", "slug": "python_best_practices"},
    {"name": "decorators",           "description": "Higher-order functions that wrap other functions to add cross-cutting behavior.", "slug": "python_best_practices"},
    {"name": "generators",           "description": "Memory-efficient iterators that yield values lazily using the yield keyword.", "slug": "python_best_practices"},
    {"name": "context_managers",     "description": "Resource lifecycle management via __enter__/__exit__ or contextlib.", "slug": "python_best_practices"},
    {"name": "dataclasses",          "description": "Auto-generated Python classes with type-annotated fields and optional immutability.", "slug": "python_best_practices"},
    {"name": "logging",              "description": "Structured, JSON-formatted operational logging using Python's logging module.", "slug": "python_best_practices"},
    {"name": "error_handling",       "description": "Exception hierarchies, domain-specific error types, and boundary error conversion.", "slug": "python_best_practices"},
    {"name": "virtual_environments", "description": "Isolated Python environments per project managed with uv or venv.", "slug": "python_best_practices"},
    # Rust (10)
    {"name": "ownership",            "description": "Rust's single-owner memory model that prevents double-free and use-after-free.", "slug": "rust_ownership"},
    {"name": "borrowing",            "description": "Temporary references to owned values without transferring ownership.", "slug": "rust_ownership"},
    {"name": "lifetimes",            "description": "Compile-time annotations ensuring references are valid for their entire use.", "slug": "rust_ownership"},
    {"name": "traits",               "description": "Rust's shared behavior abstractions, similar to interfaces in other languages.", "slug": "rust_ownership"},
    {"name": "enums",                "description": "Algebraic data types in Rust where each variant can carry different data.", "slug": "rust_ownership"},
    {"name": "pattern_matching",     "description": "Exhaustive, compile-verified branching over enum variants and data shapes.", "slug": "rust_ownership"},
    {"name": "error_handling_rust",  "description": "Result<T,E> and ? operator for propagating errors as values in Rust.", "slug": "rust_ownership"},
    {"name": "async_runtime",        "description": "Tokio-based async execution model for non-blocking I/O in Rust.", "slug": "rust_ownership"},
    {"name": "smart_pointers",       "description": "Box, Rc, Arc, and RefCell for heap allocation and shared ownership in Rust.", "slug": "rust_ownership"},
    {"name": "unsafe_rust",          "description": "Opt-in escape hatch that disables borrow checker guarantees for low-level code.", "slug": "rust_ownership"},
    # TypeScript (9)
    {"name": "generics",             "description": "Type parameters that let functions and interfaces work across multiple types.", "slug": "typescript_patterns"},
    {"name": "type_guards",          "description": "Narrowing union types at runtime with typeof, instanceof, or user-defined predicates.", "slug": "typescript_patterns"},
    {"name": "utility_types",        "description": "Built-in TypeScript transformations: Partial, Pick, Omit, Record, Readonly.", "slug": "typescript_patterns"},
    {"name": "react_hooks",          "description": "Typed custom hooks with generics for data fetching, reducers, and state.", "slug": "typescript_patterns"},
    {"name": "module_patterns",      "description": "Barrel files, type-only imports, and namespace organization in TypeScript.", "slug": "typescript_patterns"},
    {"name": "strict_mode",          "description": "TypeScript compiler strictness flags eliminating implicit any and null unsafety.", "slug": "typescript_patterns"},
    {"name": "type_inference",       "description": "Automatic type deduction by the TypeScript compiler without explicit annotation.", "slug": "typescript_patterns"},
    {"name": "discriminated_unions", "description": "Tagged union types with a shared literal discriminant for exhaustive pattern matching.", "slug": "typescript_patterns"},
    {"name": "mapped_types",         "description": "Type-level iteration over keys to transform object types systematically.", "slug": "typescript_patterns"},
    # System Design (9)
    {"name": "microservices",        "description": "Independently deployable services each owning a bounded context and its database.", "slug": "system_design"},
    {"name": "api_gateway",          "description": "Single entry point that handles auth, rate limiting, and routing for all services.", "slug": "system_design"},
    {"name": "caching",              "description": "Cache-aside, write-through, and write-behind strategies for reducing DB load.", "slug": "system_design"},
    {"name": "load_balancing",       "description": "Distributing requests across instances using round-robin, least-connections, or hashing.", "slug": "system_design"},
    {"name": "database_sharding",    "description": "Horizontal partitioning of data across multiple database instances by shard key.", "slug": "system_design"},
    {"name": "event_driven",         "description": "Async service communication via durable event streams (NATS, Kafka).", "slug": "system_design"},
    {"name": "circuit_breaker",      "description": "Failure isolation pattern that stops requests to unhealthy downstream services.", "slug": "system_design"},
    {"name": "rate_limiting",        "description": "Token-bucket and sliding-window algorithms to throttle API traffic per client.", "slug": "system_design"},
    {"name": "monitoring",           "description": "Metrics, logs, and distributed traces for observing system health and diagnosing issues.", "slug": "system_design"},
    # API Design (9)
    {"name": "rest_conventions",     "description": "Resource-oriented URL design and correct HTTP method semantics for REST APIs.", "slug": "api_design_guide"},
    {"name": "versioning",           "description": "URL and header-based API versioning strategies for backward-compatible evolution.", "slug": "api_design_guide"},
    {"name": "pagination",           "description": "Cursor-based and offset-based strategies for returning large collections safely.", "slug": "api_design_guide"},
    {"name": "authentication",       "description": "JWT access tokens, refresh token rotation, and API key patterns for API auth.", "slug": "api_design_guide"},
    {"name": "error_formats",        "description": "Consistent machine-readable error codes and HTTP status mapping for API errors.", "slug": "api_design_guide"},
    {"name": "idempotency",          "description": "Idempotency keys for safe retry of payment and mutation endpoints.", "slug": "api_design_guide"},
    {"name": "rate_limiting_api",    "description": "Per-user and per-org rate limit headers and 429 responses for public APIs.", "slug": "api_design_guide"},
    {"name": "documentation",        "description": "OpenAPI-driven developer documentation with examples, changelogs, and migration guides.", "slug": "api_design_guide"},
    {"name": "openapi",              "description": "Machine-readable API specification used for SDK generation and interactive docs.", "slug": "api_design_guide"},
]

# (prerequisite_name, dependent_name) — prerequisite must be learned before dependent
_DEMO_PREREQUISITES: list[tuple[str, str]] = [
    ("ownership",        "borrowing"),
    ("borrowing",        "lifetimes"),
    ("ownership",        "smart_pointers"),
    ("ownership",        "unsafe_rust"),
    ("type_inference",   "generics"),
    ("generics",         "type_guards"),
    ("generics",         "mapped_types"),
    ("generics",         "utility_types"),
    ("type_inference",   "discriminated_unions"),
    ("error_handling",   "async_await"),
    ("context_managers", "generators"),
    ("rest_conventions", "pagination"),
    ("rest_conventions", "versioning"),
    ("rest_conventions", "error_formats"),
    ("authentication",   "idempotency"),
    ("authentication",   "rate_limiting_api"),
    ("microservices",    "api_gateway"),
    ("microservices",    "circuit_breaker"),
    ("microservices",    "event_driven"),
    ("load_balancing",   "caching"),
    ("load_balancing",   "database_sharding"),
    ("api_gateway",      "rate_limiting"),
    ("openapi",          "documentation"),
]


def _split_into_chunks(content: str, target_words: int = 200) -> list[str]:
    """Split text into chunks of approximately target_words words each."""
    words = content.split()
    chunks: list[str] = []
    for i in range(0, len(words), target_words):
        chunk = " ".join(words[i : i + target_words])
        if chunk:
            chunks.append(chunk)
    return chunks


def _random_embedding(dim: int = 768) -> list[float]:
    """Generate a random unit vector of the given dimension."""
    vec = [random.gauss(0.0, 1.0) for _ in range(dim)]
    magnitude = math.sqrt(sum(v * v for v in vec))
    return [v / magnitude for v in vec]


async def seed_rag_documents(rag_pool: asyncpg.Pool) -> None:
    """Seed 5 technical documents with chunks, concepts, and prerequisites for demo org. Idempotent."""
    first_doc_id = next(iter(DEMO_DOC_IDS.values()))
    existing = await rag_pool.fetchval(
        "SELECT id FROM documents WHERE id = $1",
        first_doc_id,
    )
    if existing:
        print("RAG documents already seeded. Skipping.")
        return

    print("Seeding RAG demo documents for Acme Engineering...")

    # 1. Insert documents and their chunks
    for doc_meta in _DEMO_DOCS:
        slug = doc_meta["slug"]
        doc_id = DEMO_DOC_IDS[slug]
        title = doc_meta["title"]
        source_path = f"demo_documents/{slug}.md"
        content = (_DEMO_DOCS_DIR / f"{slug}.md").read_text()

        await rag_pool.execute(
            """
            INSERT INTO documents (id, organization_id, source_type, source_path, title, content, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, '{}')
            ON CONFLICT (id) DO NOTHING
            """,
            doc_id,
            DEMO_ORG_ID,
            "file",
            source_path,
            title,
            content,
        )

        chunks = _split_into_chunks(content)
        for chunk_index, chunk_text in enumerate(chunks):
            embedding = _random_embedding()
            embedding_str = "[" + ",".join(f"{v:.6f}" for v in embedding) + "]"
            await rag_pool.execute(
                """
                INSERT INTO chunks (document_id, content, chunk_index, embedding, metadata)
                VALUES ($1, $2, $3, $4, '{}')
                """,
                doc_id,
                chunk_text,
                chunk_index,
                embedding_str,
            )

    print(f"  Inserted {len(_DEMO_DOCS)} documents with chunks")

    # 2. Upsert concepts and collect their IDs for relationship wiring
    concept_ids: dict[str, str] = {}
    slug_to_doc_id: dict[str, str] = {doc["slug"]: DEMO_DOC_IDS[doc["slug"]] for doc in _DEMO_DOCS}

    for concept in _DEMO_CONCEPTS:
        source_doc_id = slug_to_doc_id[concept["slug"]]
        concept_id = await rag_pool.fetchval(
            """
            INSERT INTO org_concepts (organization_id, name, description, source_document_id)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (organization_id, name)
            DO UPDATE SET description = EXCLUDED.description,
                          source_document_id = COALESCE(EXCLUDED.source_document_id, org_concepts.source_document_id)
            RETURNING id
            """,
            DEMO_ORG_ID,
            concept["name"],
            concept["description"],
            source_doc_id,
        )
        concept_ids[concept["name"]] = str(concept_id)

    print(f"  Upserted {len(_DEMO_CONCEPTS)} concepts")

    # 3. Insert prerequisite relationships
    rel_count = 0
    for prereq_name, dependent_name in _DEMO_PREREQUISITES:
        prereq_id = concept_ids.get(prereq_name)
        dependent_id = concept_ids.get(dependent_name)
        if prereq_id and dependent_id:
            await rag_pool.execute(
                """
                INSERT INTO concept_relationships (concept_id, related_concept_id, relationship_type)
                VALUES ($1, $2, $3)
                ON CONFLICT (concept_id, related_concept_id) DO NOTHING
                """,
                prereq_id,
                dependent_id,
                "prerequisite",
            )
            rel_count += 1

    print(f"  Inserted {rel_count} prerequisite relationships")
    print("RAG documents seeding complete!")


# ---------------------------------------------------------------------------
# Demo B2B learning data — concepts, mastery, missions, flashcards, etc.
# ---------------------------------------------------------------------------

DEMO_FAKE_COURSE_ID = "00000000-0000-4000-d000-000000000001"

# Deterministic member UUIDs — same values used in identity-db and learning-db
_DEMO_MEMBER_UUIDS = [
    _DEMO_MEMBER_UUIDS_MAP[f"{prefix}@acme.com"]
    for _name, prefix in _DEMO_MEMBERS
]

# Concept groups by topic (indices into _DEMO_CONCEPTS)
_PYTHON_CONCEPTS = list(range(0, 10))
_RUST_CONCEPTS = list(range(10, 20))
_TS_CONCEPTS = list(range(20, 29))
_SYSDESIGN_CONCEPTS = list(range(29, 38))
_API_CONCEPTS = list(range(38, 47))

# Member specialisations — each member is strong in one area
_MEMBER_STRENGTHS: list[list[int]] = [
    _PYTHON_CONCEPTS,      # Sarah Kim
    _RUST_CONCEPTS,        # Mike Johnson
    _TS_CONCEPTS,          # Priya Patel
    _SYSDESIGN_CONCEPTS,   # James Wilson
    _API_CONCEPTS,         # Yuki Tanaka
    _PYTHON_CONCEPTS,      # Carlos Rodriguez
    _RUST_CONCEPTS,        # Emma Davis
    _TS_CONCEPTS,          # Ali Hassan
    _SYSDESIGN_CONCEPTS,   # Lisa Chen
]


async def seed_demo_learning(learning_pool: asyncpg.Pool) -> None:
    """Seed B2B learning data for demo user + 9 team members. Idempotent."""
    existing = await learning_pool.fetchval(
        "SELECT user_id FROM trust_levels WHERE user_id = $1",
        DEMO_USER_ID,
    )
    if existing:
        print("Demo learning data already seeded. Skipping.")
        return

    print("Seeding demo B2B learning data...")
    now = datetime.now(timezone.utc)
    today = date.today()

    # ------------------------------------------------------------------
    # 1. Seed 47 concepts into learning.concepts
    # ------------------------------------------------------------------
    concept_ids: list[str] = []
    for i, concept in enumerate(_DEMO_CONCEPTS):
        cid = await learning_pool.fetchval(
            """
            INSERT INTO concepts (course_id, name, description, "order")
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (course_id, name) DO UPDATE SET description = EXCLUDED.description
            RETURNING id
            """,
            DEMO_FAKE_COURSE_ID,
            concept["name"],
            concept["description"],
            i,
        )
        concept_ids.append(str(cid))
    print(f"  Inserted {len(concept_ids)} concepts into learning DB")

    # ------------------------------------------------------------------
    # 2. Concept mastery for demo user (all 47)
    #    10 mastered (0.80-0.95), 15 in-progress (0.40-0.60), 22 gaps (0.05-0.25)
    # ------------------------------------------------------------------
    mastered_indices = random.sample(range(47), 10)
    remaining = [i for i in range(47) if i not in mastered_indices]
    in_progress_indices = random.sample(remaining, 15)
    gap_indices = [i for i in remaining if i not in in_progress_indices]

    for idx in range(47):
        if idx in mastered_indices:
            mastery = round(random.uniform(0.80, 0.95), 2)
        elif idx in in_progress_indices:
            mastery = round(random.uniform(0.40, 0.60), 2)
        else:
            mastery = round(random.uniform(0.05, 0.25), 2)
        await learning_pool.execute(
            """
            INSERT INTO concept_mastery (student_id, concept_id, mastery)
            VALUES ($1, $2, $3)
            ON CONFLICT (student_id, concept_id) DO NOTHING
            """,
            DEMO_USER_ID,
            concept_ids[idx],
            mastery,
        )
    print("  Seeded concept mastery for demo user (10 mastered, 15 in-progress, 22 gaps)")

    # ------------------------------------------------------------------
    # 3. Concept mastery for 9 team members
    # ------------------------------------------------------------------
    for member_idx, member_uuid in enumerate(_DEMO_MEMBER_UUIDS):
        strong_indices = _MEMBER_STRENGTHS[member_idx]
        for idx in range(47):
            if idx in strong_indices:
                mastery = round(random.uniform(0.65, 0.95), 2)
            else:
                mastery = round(random.uniform(0.05, 0.45), 2)
            await learning_pool.execute(
                """
                INSERT INTO concept_mastery (student_id, concept_id, mastery)
                VALUES ($1, $2, $3)
                ON CONFLICT (student_id, concept_id) DO NOTHING
                """,
                member_uuid,
                concept_ids[idx],
                mastery,
            )
    print("  Seeded concept mastery for 9 team members")

    # ------------------------------------------------------------------
    # 4. Missions for demo user (15 completed + 1 pending)
    # ------------------------------------------------------------------
    _completed_blueprints = [
        {"title": "Build a REST API", "steps": [{"id": 1, "description": "Design endpoints", "completed": True}, {"id": 2, "description": "Implement handlers", "completed": True}, {"id": 3, "description": "Add validation", "completed": True}], "difficulty": "intermediate", "estimated_minutes": 30},
        {"title": "Refactor with Type Hints", "steps": [{"id": 1, "description": "Add return types", "completed": True}, {"id": 2, "description": "Annotate parameters", "completed": True}, {"id": 3, "description": "Fix mypy errors", "completed": True}], "difficulty": "beginner", "estimated_minutes": 20},
        {"title": "Async Data Pipeline", "steps": [{"id": 1, "description": "Create async generators", "completed": True}, {"id": 2, "description": "Add error handling", "completed": True}, {"id": 3, "description": "Benchmark throughput", "completed": True}], "difficulty": "advanced", "estimated_minutes": 45},
        {"title": "Implement Circuit Breaker", "steps": [{"id": 1, "description": "Define states", "completed": True}, {"id": 2, "description": "Add failure counting", "completed": True}, {"id": 3, "description": "Write recovery logic", "completed": True}], "difficulty": "intermediate", "estimated_minutes": 35},
        {"title": "Design Database Schema", "steps": [{"id": 1, "description": "Identify entities", "completed": True}, {"id": 2, "description": "Define relationships", "completed": True}, {"id": 3, "description": "Add indexes", "completed": True}], "difficulty": "intermediate", "estimated_minutes": 25},
    ]

    _pending_blueprint = {
        "title": "Build a REST API with Authentication",
        "steps": [
            {"id": 1, "description": "Design JWT token flow", "completed": False},
            {"id": 2, "description": "Implement login endpoint", "completed": False},
            {"id": 3, "description": "Add role-based middleware", "completed": False},
            {"id": 4, "description": "Write integration tests", "completed": False},
        ],
        "difficulty": "intermediate",
        "estimated_minutes": 30,
    }

    for day_offset in range(15):
        days_ago = 14 - day_offset
        completed_at = now - timedelta(days=days_ago, hours=random.randint(1, 12))
        score = round(random.uniform(0.65, 0.95), 2)
        mastery_delta = round(random.uniform(0.05, 0.15), 2)
        concept_id = concept_ids[day_offset % len(concept_ids)]
        blueprint = _completed_blueprints[day_offset % len(_completed_blueprints)]
        await learning_pool.execute(
            """
            INSERT INTO missions (
                user_id, organization_id, concept_id, mission_type, status,
                blueprint, score, mastery_delta, started_at, completed_at, created_at
            )
            VALUES ($1, $2, $3, 'daily', 'completed', $4::jsonb, $5, $6, $7, $8, $9)
            """,
            DEMO_USER_ID,
            DEMO_ORG_ID,
            concept_id,
            json.dumps(blueprint),
            score,
            mastery_delta,
            completed_at - timedelta(minutes=random.randint(15, 45)),
            completed_at,
            completed_at - timedelta(minutes=random.randint(45, 90)),
        )

    # 1 pending mission (today)
    await learning_pool.execute(
        """
        INSERT INTO missions (
            user_id, organization_id, concept_id, mission_type, status,
            blueprint, created_at
        )
        VALUES ($1, $2, $3, 'daily', 'pending', $4::jsonb, $5)
        """,
        DEMO_USER_ID,
        DEMO_ORG_ID,
        concept_ids[15],
        json.dumps(_pending_blueprint),
        now,
    )
    print("  Seeded 16 missions (15 completed + 1 pending) with realistic blueprints")

    # ------------------------------------------------------------------
    # 5. Flashcards for demo user (25 total)
    # ------------------------------------------------------------------
    flashcard_concepts = random.sample(_DEMO_CONCEPTS, 25)
    for i, fc in enumerate(flashcard_concepts):
        if i < 10:
            # Due today
            due = now - timedelta(hours=random.randint(0, 6))
        else:
            # Due in future (reviewed recently)
            due = now + timedelta(days=random.randint(1, 14))
        stability = round(random.uniform(1.0, 10.0), 2)
        difficulty = round(random.uniform(0.1, 0.9), 2)
        reps = random.randint(1, 8)
        await learning_pool.execute(
            """
            INSERT INTO flashcards (
                student_id, course_id, concept, answer,
                stability, difficulty, due, reps, state, last_review, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 2, $9, $10)
            """,
            DEMO_USER_ID,
            DEMO_FAKE_COURSE_ID,
            fc["name"],
            fc["description"],
            stability,
            difficulty,
            due,
            reps,
            now - timedelta(days=random.randint(1, 7)),
            now - timedelta(days=random.randint(7, 21)),
        )
    print("  Seeded 25 flashcards (10 due today, 15 future)")

    # ------------------------------------------------------------------
    # 6. Trust levels
    # ------------------------------------------------------------------
    await learning_pool.execute(
        """
        INSERT INTO trust_levels (
            user_id, organization_id, level,
            total_missions_completed, total_concepts_mastered, unlocked_areas
        )
        VALUES ($1, $2, 4, 15, 10, $3)
        ON CONFLICT (user_id) DO NOTHING
        """,
        DEMO_USER_ID,
        DEMO_ORG_ID,
        json.dumps(["python", "rust", "typescript", "system_design"]),
    )

    member_levels = [2, 3, 1, 2, 3, 1, 2, 1, 3]
    for member_idx, member_uuid in enumerate(_DEMO_MEMBER_UUIDS):
        lvl = member_levels[member_idx]
        missions_done = lvl * random.randint(3, 6)
        concepts_done = lvl * random.randint(2, 4)
        await learning_pool.execute(
            """
            INSERT INTO trust_levels (
                user_id, organization_id, level,
                total_missions_completed, total_concepts_mastered, unlocked_areas
            )
            VALUES ($1, $2, $3, $4, $5, '[]')
            ON CONFLICT (user_id) DO NOTHING
            """,
            member_uuid,
            DEMO_ORG_ID,
            lvl,
            missions_done,
            concepts_done,
        )
    print("  Seeded trust levels (demo=4, team=1-3)")

    # ------------------------------------------------------------------
    # 7. Streaks for demo user
    # ------------------------------------------------------------------
    await learning_pool.execute(
        """
        INSERT INTO streaks (user_id, current_streak, longest_streak, last_activity_date)
        VALUES ($1, 7, 14, $2)
        ON CONFLICT (user_id) DO NOTHING
        """,
        DEMO_USER_ID,
        today,
    )
    print("  Seeded streak (current=7, longest=14)")

    # ------------------------------------------------------------------
    # 8. XP events (20 over 14 days, ~2450 total)
    # ------------------------------------------------------------------
    # 15 mission_complete (750) + 20 flashcard_review (100) + 16 concept_mastered (1600) = 2450
    xp_plan: list[tuple[str, int]] = (
        [("mission_complete", 50)] * 15
        + [("flashcard_review", 5)] * 20
        + [("concept_mastered", 100)] * 16
    )
    random.shuffle(xp_plan)
    # Take first 20 events
    xp_plan = xp_plan[:20]
    for i, (action, points) in enumerate(xp_plan):
        days_ago = 14 - (i * 14 // 20)
        created_at = now - timedelta(days=days_ago, hours=random.randint(1, 18))
        await learning_pool.execute(
            """
            INSERT INTO xp_events (user_id, action, points, course_id, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            DEMO_USER_ID,
            action,
            points,
            DEMO_FAKE_COURSE_ID,
            created_at,
        )
    total_xp = sum(p for _, p in xp_plan)
    print(f"  Seeded {len(xp_plan)} XP events ({total_xp} total XP)")

    # ------------------------------------------------------------------
    # 9. Badges for demo user
    # ------------------------------------------------------------------
    badge_types = ["first_enrollment", "streak_7", "quiz_ace"]
    for bt in badge_types:
        await learning_pool.execute(
            """
            INSERT INTO badges (user_id, badge_type, unlocked_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, badge_type) DO NOTHING
            """,
            DEMO_USER_ID,
            bt,
            now - timedelta(days=random.randint(1, 14)),
        )
    print(f"  Seeded {len(badge_types)} badges")

    # ------------------------------------------------------------------
    # 10. Activity feed (20 entries over 14 days)
    # ------------------------------------------------------------------
    activity_templates = [
        ("mission_completed", lambda: {"concept": random.choice(_DEMO_CONCEPTS)["name"], "score": round(random.uniform(0.70, 0.95), 2)}),
        ("badge_earned", lambda: {"badge": random.choice(badge_types)}),
        ("streak_milestone", lambda: {"days": random.choice([3, 5, 7, 10, 14])}),
        ("flashcard_review", lambda: {"concept": random.choice(_DEMO_CONCEPTS)["name"], "cards_reviewed": random.randint(5, 15)}),
        ("concept_mastered", lambda: {"concept": random.choice(_DEMO_CONCEPTS)["name"], "mastery": round(random.uniform(0.80, 0.95), 2)}),
    ]
    for i in range(20):
        days_ago = 14 - (i * 14 // 20)
        created_at = now - timedelta(days=days_ago, hours=random.randint(1, 18))
        activity_type, payload_fn = activity_templates[i % len(activity_templates)]
        await learning_pool.execute(
            """
            INSERT INTO activity_feed (user_id, activity_type, payload, created_at)
            VALUES ($1, $2, $3, $4)
            """,
            DEMO_USER_ID,
            activity_type,
            json.dumps(payload_fn()),
            created_at,
        )
    print("  Seeded 20 activity feed entries")

    print("Demo B2B learning data seeding complete!")


async def seed_demo_notifications(notification_pool: asyncpg.Pool) -> None:
    """Seed ~10 notifications for the demo user. Idempotent."""
    existing = await notification_pool.fetchval(
        "SELECT count(*) FROM notifications WHERE user_id = $1",
        DEMO_USER_ID,
    )
    if existing and existing > 0:
        print("Demo notifications already seeded. Skipping.")
        return

    print("Seeding demo notifications...")
    now = datetime.now(timezone.utc)

    notifications = [
        # 1 welcome
        ("welcome", "Welcome to KnowledgeOS!", "Your team workspace is ready. Start exploring missions and build your knowledge graph.", False, now - timedelta(days=14)),
        # 2 reminders (streak_reminder, flashcard_reminder)
        ("streak_reminder", "Keep your streak alive!", "You have 3 hours left to maintain your 7-day streak.", False, now - timedelta(days=1, hours=6)),
        ("flashcard_reminder", "Flashcards due for review", "You have 10 flashcards due today across Python and Rust concepts.", False, now - timedelta(hours=4)),
        # 3 course_completed (used as achievement/badge notifications)
        ("course_completed", "Badge earned: First Enrollment", "Congratulations! You unlocked the First Enrollment badge.", False, now - timedelta(days=12)),
        ("course_completed", "Badge earned: Quiz Ace", "You scored 100% on a quiz! Quiz Ace badge unlocked.", False, now - timedelta(days=8)),
        ("course_completed", "Badge earned: 7-Day Streak", "Amazing consistency! You maintained a 7-day learning streak.", False, now - timedelta(days=5)),
        # 2 enrollment (team activity)
        ("enrollment", "Sarah Kim completed a mission", "Your teammate Sarah scored 92% on the async_await mission.", False, now - timedelta(days=3)),
        ("enrollment", "New team member joined", "Ali Hassan has joined Acme Engineering workspace.", False, now - timedelta(days=10)),
        # 2 read notifications
        ("registration", "Verify your email", "Please verify your email address to unlock all features.", True, now - timedelta(days=14)),
        ("payment", "Enterprise plan activated", "Your Acme Engineering workspace is now on the Enterprise plan.", True, now - timedelta(days=13)),
    ]

    for ntype, title, body, is_read, created_at in notifications:
        await notification_pool.execute(
            """
            INSERT INTO notifications (user_id, type, title, body, is_read, created_at)
            VALUES ($1, $2::notification_type, $3, $4, $5, $6)
            """,
            DEMO_USER_ID,
            ntype,
            title,
            body,
            is_read,
            created_at,
        )

    print(f"  Seeded {len(notifications)} notifications (2 read, 8 unread)")
    print("Demo notifications seeding complete!")


async def seed_demo_enrollments(
    enrollment_pool: asyncpg.Pool,
    course_pool: asyncpg.Pool,
) -> None:
    """Seed enrollments and lesson progress for demo user. Idempotent."""
    existing = await enrollment_pool.fetchval(
        "SELECT count(*) FROM enrollments WHERE student_id = $1",
        DEMO_USER_ID,
    )
    if existing and existing > 0:
        print("Demo enrollments already seeded. Skipping.")
        return

    print("Seeding demo enrollments...")

    # Pick 5 courses that have modules and lessons
    course_rows = await course_pool.fetch(
        "SELECT id FROM courses LIMIT 5"
    )
    if not course_rows:
        print("  No courses found. Skipping demo enrollments.")
        return
    course_ids = [str(r["id"]) for r in course_rows]

    # Insert enrollments
    for i, course_id in enumerate(course_ids):
        status = "completed" if i < 2 else "in_progress" if i < 4 else "enrolled"
        await enrollment_pool.execute(
            """
            INSERT INTO enrollments (student_id, course_id, status)
            VALUES ($1, $2, $3::enrollment_status)
            ON CONFLICT (student_id, course_id) DO NOTHING
            """,
            DEMO_USER_ID,
            course_id,
            status,
        )
    print(f"  Enrolled demo user in {len(course_ids)} courses (2 completed, 2 in-progress, 1 enrolled)")

    # Fetch lessons for these courses to create progress records
    lesson_rows = await course_pool.fetch(
        """
        SELECT l.id as lesson_id, m.course_id
        FROM lessons l
        JOIN modules m ON l.module_id = m.id
        WHERE m.course_id = ANY($1::uuid[])
        ORDER BY m."order", l."order"
        """,
        [r["id"] for r in course_rows],
    )

    # Group lessons by course
    course_lessons: dict[str, list[str]] = {}
    for row in lesson_rows:
        cid = str(row["course_id"])
        course_lessons.setdefault(cid, []).append(str(row["lesson_id"]))

    progress_count = 0
    now = datetime.now(timezone.utc)
    for i, course_id in enumerate(course_ids):
        lessons = course_lessons.get(course_id, [])
        if not lessons:
            continue

        if i < 2:
            # Completed courses: all lessons done
            selected = lessons
        elif i < 4:
            # In-progress: ~60% of lessons done
            count = max(1, int(len(lessons) * 0.6))
            selected = lessons[:count]
        else:
            # Enrolled: no progress yet
            selected = []

        for lesson_id in selected:
            days_ago = random.randint(1, 30)
            completed_at = now - timedelta(days=days_ago, hours=random.randint(0, 12))
            await enrollment_pool.execute(
                """
                INSERT INTO lesson_progress (student_id, lesson_id, course_id, completed_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (student_id, lesson_id) DO NOTHING
                """,
                DEMO_USER_ID,
                lesson_id,
                course_id,
                completed_at,
            )
            progress_count += 1

    print(f"  Seeded {progress_count} lesson progress records")
    print("Demo enrollments seeding complete!")


async def main() -> None:
    identity_pool = await asyncpg.create_pool(IDENTITY_DB_URL, min_size=2, max_size=5)
    course_pool = await asyncpg.create_pool(COURSE_DB_URL, min_size=2, max_size=5)
    enrollment_pool = await asyncpg.create_pool(ENROLLMENT_DB_URL, min_size=2, max_size=5)
    payment_pool = await asyncpg.create_pool(PAYMENT_DB_URL, min_size=2, max_size=5)
    notification_pool = await asyncpg.create_pool(NOTIFICATION_DB_URL, min_size=2, max_size=5)
    learning_pool = await asyncpg.create_pool(LEARNING_DB_URL, min_size=2, max_size=5)
    rag_pool = await asyncpg.create_pool(RAG_DB_URL, min_size=2, max_size=5)

    try:
        # Check if already seeded
        count = await identity_pool.fetchval("SELECT count(*) FROM users")
        if count >= USER_COUNT:
            print(f"Already seeded ({count} users). Checking learning data...")
            # Still try to seed learning data if it's missing
            student_rows = await identity_pool.fetch("SELECT id FROM users WHERE role = 'student'")
            student_ids = [str(row["id"]) for row in student_rows]
            await seed_learning(learning_pool, course_pool, enrollment_pool, student_ids)
            await seed_demo_org(identity_pool, payment_pool)
            await seed_rag_documents(rag_pool)
            await seed_demo_learning(learning_pool)
            await seed_demo_notifications(notification_pool)
            await seed_demo_enrollments(enrollment_pool, course_pool)
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

        await seed_demo_org(identity_pool, payment_pool)
        await seed_rag_documents(rag_pool)
        await seed_demo_learning(learning_pool)
        await seed_demo_notifications(notification_pool)
        await seed_demo_enrollments(enrollment_pool, course_pool)

        print("Seeding complete!")
    finally:
        await identity_pool.close()
        await course_pool.close()
        await enrollment_pool.close()
        await payment_pool.close()
        await notification_pool.close()
        await learning_pool.close()
        await rag_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
