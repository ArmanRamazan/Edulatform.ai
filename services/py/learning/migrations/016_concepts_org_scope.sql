-- B2B org-scoping for concepts.
--
-- Concept model overview:
--   learning.concepts      — operational layer: mastery tracking, quiz targets, knowledge graph.
--                            Tied to courses/lessons (B2C) or organisations (B2B, organization_id set).
--   rag.org_concepts       — source-of-truth for B2B: extracted from ingested documents.
--                            Future: rag → learning sync on document ingestion event.
--
-- organization_id is nullable for backward compatibility with B2C courses.
-- B2B missions use concepts scoped to their organisation.

ALTER TABLE concepts ADD COLUMN IF NOT EXISTS organization_id UUID;

CREATE INDEX IF NOT EXISTS idx_concepts_org ON concepts(organization_id) WHERE organization_id IS NOT NULL;
