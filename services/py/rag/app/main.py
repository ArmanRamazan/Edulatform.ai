from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import asyncpg
import httpx
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from common.database import create_pool, update_pool_metrics
from common.errors import register_error_handlers
from common.health import create_health_router
from common.logging import configure_logging
from app.config import Settings
from app.repositories.embedding_client import (
    EmbeddingClient,
    GeminiEmbeddingClient,
    StubEmbeddingClient,
)
from app.repositories.document_repository import DocumentRepository
from app.repositories.search_repository import SearchRepository
from app.repositories.concept_store import ConceptStoreRepository
from app.routes.ingestion_routes import create_ingestion_router
from app.routes.search_routes import create_search_router
from app.routes.concept_routes import create_concept_router
from app.routes.knowledge_base_routes import create_knowledge_base_router
from app.services.ingestion_service import IngestionService
from app.services.search_service import SearchService
from app.services.extraction_service import ExtractionService
from app.services.knowledge_base_service import KnowledgeBaseService

app_settings = Settings()

_pool: asyncpg.Pool | None = None
_http_client: httpx.AsyncClient | None = None
_embedding_client: EmbeddingClient | None = None
_ingestion_service: IngestionService | None = None
_search_service: SearchService | None = None
_extraction_service: ExtractionService | None = None
_concept_store: ConceptStoreRepository | None = None
_kb_service: KnowledgeBaseService | None = None


def get_embedding_client() -> EmbeddingClient:
    assert _embedding_client is not None
    return _embedding_client


def get_ingestion_service() -> IngestionService:
    assert _ingestion_service is not None
    return _ingestion_service


def get_search_service() -> SearchService:
    assert _search_service is not None
    return _search_service


def get_extraction_service() -> ExtractionService:
    assert _extraction_service is not None
    return _extraction_service


def get_concept_store() -> ConceptStoreRepository:
    assert _concept_store is not None
    return _concept_store


def get_kb_service() -> KnowledgeBaseService:
    assert _kb_service is not None
    return _kb_service


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _pool, _http_client, _embedding_client, _ingestion_service, _search_service, _extraction_service, _concept_store, _kb_service

    configure_logging(service_name="rag")
    logger = structlog.get_logger()

    _pool = await create_pool(
        app_settings.database_url,
        min_size=app_settings.db_pool_min_size,
        max_size=app_settings.db_pool_max_size,
    )

    async with _pool.acquire() as conn:
        with open("migrations/001_init.sql") as f:
            await conn.execute(f.read())
        with open("migrations/002_concepts.sql") as f:
            await conn.execute(f.read())

    _http_client = httpx.AsyncClient()
    if app_settings.openai_api_key:
        _embedding_client = GeminiEmbeddingClient(
            http_client=_http_client,
            api_key=app_settings.openai_api_key,
            model=app_settings.embedding_model,
        )
        logger.info("embedding_client", mode="gemini", model=app_settings.embedding_model)
    else:
        _embedding_client = StubEmbeddingClient(dimensions=app_settings.embedding_dimensions)
        logger.info("embedding_client", mode="stub")

    doc_repo = DocumentRepository(_pool)
    search_repo = SearchRepository(_pool)
    _concept_store = ConceptStoreRepository(_pool)
    _extraction_service = ExtractionService(
        concept_store=_concept_store,
        http_client=_http_client,
        settings=app_settings,
    )
    _ingestion_service = IngestionService(
        document_repo=doc_repo,
        embedding_client=_embedding_client,
        extraction_service=_extraction_service,
    )
    _search_service = SearchService(
        search_repo=search_repo,
        embedding_client=_embedding_client,
    )
    _kb_service = KnowledgeBaseService(
        document_repo=doc_repo,
        concept_store=_concept_store,
        ingestion_service=_ingestion_service,
        search_service=_search_service,
    )

    logger.info("service_started", port=8008)
    yield

    await _http_client.aclose()
    await _pool.close()


app = FastAPI(title="RAG Service", lifespan=lifespan)
register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(create_health_router(lambda: _pool))
app.include_router(
    create_ingestion_router(
        get_service=get_ingestion_service,
        jwt_secret=app_settings.jwt_secret,
        jwt_algorithm=app_settings.jwt_algorithm,
    )
)
app.include_router(
    create_search_router(
        get_service=get_search_service,
        jwt_secret=app_settings.jwt_secret,
        jwt_algorithm=app_settings.jwt_algorithm,
    )
)
app.include_router(
    create_concept_router(
        get_extraction_service=get_extraction_service,
        get_concept_store=get_concept_store,
        jwt_secret=app_settings.jwt_secret,
        jwt_algorithm=app_settings.jwt_algorithm,
    )
)
app.include_router(
    create_knowledge_base_router(
        get_service=get_kb_service,
        jwt_secret=app_settings.jwt_secret,
        jwt_algorithm=app_settings.jwt_algorithm,
    )
)


@app.middleware("http")
async def pool_metrics_middleware(request, call_next):  # type: ignore[no-untyped-def]
    if _pool is not None:
        update_pool_metrics(_pool, "rag")
    return await call_next(request)


Instrumentator().instrument(app).expose(app)
