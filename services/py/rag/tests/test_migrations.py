import os


def test_init_migration_exists() -> None:
    migration_path = os.path.join(
        os.path.dirname(__file__), "..", "migrations", "001_init.sql"
    )
    assert os.path.exists(migration_path), "migrations/001_init.sql must exist"


def test_init_migration_contains_required_tables() -> None:
    migration_path = os.path.join(
        os.path.dirname(__file__), "..", "migrations", "001_init.sql"
    )
    with open(migration_path) as f:
        content = f.read()

    assert "CREATE EXTENSION IF NOT EXISTS vector" in content
    assert "CREATE TABLE IF NOT EXISTS documents" in content
    assert "CREATE TABLE IF NOT EXISTS chunks" in content
    assert "vector(768)" in content
    assert "idx_chunks_embedding" in content
    assert "idx_documents_org" in content
    assert "idx_chunks_document" in content
