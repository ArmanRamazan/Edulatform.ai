DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'is_public'
    ) THEN
        ALTER TABLE users ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT true;
    END IF;
END $$;
