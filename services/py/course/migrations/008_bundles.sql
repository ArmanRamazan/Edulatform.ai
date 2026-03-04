CREATE TABLE IF NOT EXISTS course_bundles (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id       UUID NOT NULL,
    title            VARCHAR(200) NOT NULL,
    description      TEXT NOT NULL DEFAULT '',
    price            NUMERIC(10,2) NOT NULL,
    discount_percent INTEGER NOT NULL CHECK (discount_percent BETWEEN 1 AND 99),
    is_active        BOOLEAN NOT NULL DEFAULT true,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bundles_teacher ON course_bundles(teacher_id);

CREATE TABLE IF NOT EXISTS bundle_courses (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bundle_id  UUID NOT NULL REFERENCES course_bundles(id) ON DELETE CASCADE,
    course_id  UUID NOT NULL,
    UNIQUE(bundle_id, course_id)
);

CREATE INDEX IF NOT EXISTS idx_bc_bundle ON bundle_courses(bundle_id);
