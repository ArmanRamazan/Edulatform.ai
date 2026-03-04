-- Concept extraction tables for knowledge graph

CREATE TABLE IF NOT EXISTS org_concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(organization_id, name)
);

CREATE TABLE IF NOT EXISTS concept_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_id UUID NOT NULL REFERENCES org_concepts(id) ON DELETE CASCADE,
    related_concept_id UUID NOT NULL REFERENCES org_concepts(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL DEFAULT 'related',
    UNIQUE(concept_id, related_concept_id)
);

CREATE INDEX IF NOT EXISTS idx_org_concepts_org ON org_concepts(organization_id);
CREATE INDEX IF NOT EXISTS idx_concept_relationships_concept ON concept_relationships(concept_id);
