import os

# Set required env vars before seed module is imported — module reads them at load time
os.environ.setdefault("IDENTITY_DB_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("COURSE_DB_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ENROLLMENT_DB_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("PAYMENT_DB_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("NOTIFICATION_DB_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("LEARNING_DB_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("RAG_DB_URL", "postgresql://test:test@localhost/test")
