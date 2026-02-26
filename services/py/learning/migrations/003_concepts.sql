-- Knowledge Graph: concepts, prerequisites, mastery tracking

CREATE TABLE IF NOT EXISTS concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL,
    lesson_id UUID,
    name VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    parent_id UUID REFERENCES concepts(id) ON DELETE SET NULL,
    "order" INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(course_id, name)
);

CREATE INDEX IF NOT EXISTS idx_concepts_course ON concepts(course_id);
CREATE INDEX IF NOT EXISTS idx_concepts_lesson ON concepts(lesson_id);

CREATE TABLE IF NOT EXISTS concept_prerequisites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    prerequisite_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    UNIQUE(concept_id, prerequisite_id),
    CHECK(concept_id != prerequisite_id)
);

CREATE TABLE IF NOT EXISTS concept_mastery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    mastery FLOAT DEFAULT 0.0,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(student_id, concept_id)
);

CREATE INDEX IF NOT EXISTS idx_mastery_student ON concept_mastery(student_id);
CREATE INDEX IF NOT EXISTS idx_mastery_concept ON concept_mastery(concept_id);
