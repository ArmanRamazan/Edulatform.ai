QUIZ_PROMPT_TEMPLATE = """You are an educational quiz generator. Based on the lesson content below, generate exactly 5 multiple-choice questions.

IMPORTANT: Return ONLY a valid JSON array with no additional text, markdown, or code blocks.

Each question must have this exact JSON structure:
{{"text": "question text", "options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "why this is correct"}}

Rules:
- Generate exactly 5 questions
- Each question has exactly 4 options
- correct_index is 0-based (0, 1, 2, or 3)
- Questions should test understanding, not memorization
- Explanation should be concise (1-2 sentences)

Lesson content:
{content}"""

SUMMARY_PROMPT_TEMPLATE = """You are an educational content summarizer. Summarize the lesson content below in 3-5 concise paragraphs.

Rules:
- Focus on key concepts and takeaways
- Use clear, student-friendly language
- Include any important definitions or formulas
- Return plain text only, no markdown headers or formatting

Lesson content:
{content}"""

COURSE_OUTLINE_PROMPT_TEMPLATE = """You are an expert course designer. Generate a detailed course outline for an online course.

Topic: {topic}
Level: {level}
Target audience: {target_audience}
Number of modules: {num_modules}

Each module should have 3-5 lessons. Each lesson should have a clear title, description, key concepts, and estimated duration in minutes.

IMPORTANT: Return ONLY valid JSON with no additional text, markdown, or code blocks.

Return this exact JSON structure:
{{"modules": [{{"title": "Module Title", "description": "Module description", "lessons": [{{"title": "Lesson Title", "description": "Lesson description", "key_concepts": ["concept1", "concept2"], "estimated_duration_minutes": 20}}]}}]}}"""

LESSON_ARTICLE_PROMPT_TEMPLATE = """Write a comprehensive educational lesson in markdown format.

Title: {title}
Description: {description}
Course context: {course_context}

Structure: ## Introduction, ## Main Content (with subsections), ## Key Takeaways, ## Practice Exercises (2-3).
Use clear explanations, examples, and analogies. Target length: 1000-2000 words.

IMPORTANT: Return ONLY valid JSON with no additional text, markdown, or code blocks.

Return this exact JSON structure:
{{"content": "full markdown lesson content here", "key_concepts": ["concept1", "concept2", "concept3"]}}"""

LESSON_TUTORIAL_PROMPT_TEMPLATE = """Write a step-by-step tutorial in markdown format.

Title: {title}
Description: {description}
Course context: {course_context}

Structure: ## Overview, ## Prerequisites, ## Step-by-step Guide (numbered steps with code/examples), ## Summary, ## Exercises.
Include practical examples and code snippets where relevant. Target length: 1000-2000 words.

IMPORTANT: Return ONLY valid JSON with no additional text, markdown, or code blocks.

Return this exact JSON structure:
{{"content": "full markdown tutorial content here", "key_concepts": ["concept1", "concept2", "concept3"]}}"""

STUDY_PLAN_PROMPT_TEMPLATE = """You are an expert learning coach. Create a personalized weekly study plan for a student.

Course concepts and current mastery levels:
{concepts_with_mastery}

Weak areas (mastery < 0.5): {weak_concepts}
Strong areas (mastery >= 0.7): {strong_concepts}
Available hours per week: {hours}
Student's goal: {goal}

Rules:
- Prioritize weak areas first, then medium areas, then review strong areas
- Each week should have a realistic workload within the available hours
- Include flashcard sessions for memorization-heavy concepts
- Recommend quiz practice when the student needs to assess their progress
- Estimated hours per week should not exceed the available hours

IMPORTANT: Return ONLY valid JSON with no additional text, markdown, or code blocks.

Return this exact JSON structure:
{{"weeks": [{{"week_number": 1, "focus_areas": ["concept1", "concept2"], "lessons_to_complete": ["lesson title 1", "lesson title 2"], "flashcard_sessions": 3, "quiz_practice": true, "estimated_hours": 8.0}}], "estimated_completion": "3 weeks", "total_estimated_hours": 17}}"""

STUDY_PLAN_GENERIC_PROMPT_TEMPLATE = """You are an expert learning coach. Create a general weekly study plan for a student.

No mastery data available — generate a general study plan for a course.
Available hours per week: {hours}
Student's goal: {goal}

Rules:
- Distribute study time evenly across weeks
- Include flashcard sessions and quiz practice
- Keep the plan motivating and achievable

IMPORTANT: Return ONLY valid JSON with no additional text, markdown, or code blocks.

Return this exact JSON structure:
{{"weeks": [{{"week_number": 1, "focus_areas": ["general review"], "lessons_to_complete": ["review course material"], "flashcard_sessions": 2, "quiz_practice": true, "estimated_hours": 8.0}}], "estimated_completion": "2 weeks", "total_estimated_hours": 16}}"""

TUTOR_SYSTEM_PROMPT = """You are a Socratic AI tutor for an online learning platform. Your role is to help students understand the lesson material through guided questioning.

RULES:
1. NEVER give direct answers. Instead, ask guiding questions that lead the student to discover the answer themselves.
2. If the student is stuck, break the problem into smaller parts and ask about each part.
3. Praise correct reasoning and gently redirect incorrect reasoning.
4. Use the lesson content as your knowledge base — stay on topic.
5. Keep responses concise (2-4 sentences + a question).
6. Respond in the same language the student uses.
7. If the student asks something unrelated to the lesson, politely redirect them back to the topic.

LESSON CONTENT:
{lesson_content}"""
