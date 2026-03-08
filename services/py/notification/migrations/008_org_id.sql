ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS organization_id UUID;

CREATE INDEX IF NOT EXISTS idx_notifications_org
    ON notifications(organization_id)
    WHERE organization_id IS NOT NULL;
