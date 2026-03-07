CREATE TABLE IF NOT EXISTS org_github_repos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    repo_url TEXT NOT NULL,
    branch TEXT NOT NULL DEFAULT 'main',
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(organization_id, repo_url)
);

CREATE INDEX IF NOT EXISTS idx_org_github_repos_org ON org_github_repos(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_github_repos_url ON org_github_repos(repo_url);
