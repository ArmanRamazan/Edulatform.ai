# 06 — Безопасность и Compliance

> Владелец: Architect / Security Lead
> Последнее обновление: 2026-03-05
>
> Обновлено под B2B pivot. Фокус на multi-tenant isolation и code security.

---

## Модель угроз (B2B context)

| Угроза | Вероятность | Импакт | Митигация |
|--------|------------|--------|-----------|
| Cross-tenant data leak | Высокая | Критический | org_id на каждом запросе, тесты на isolation |
| Company code exposure | Высокая | Критический | Encrypted at rest, access controls, no raw code в logs |
| SQL Injection / XSS | Высокая | Критический | Parameterized queries, Pydantic validation, CSP headers |
| Account takeover | Средняя | Критический | Rate limiting, JWT rotation, anomaly detection |
| LLM data leakage | Средняя | Высокий | No PII в prompts, org-scoped context only |
| GitHub token theft | Средняя | Высокий | Encrypted storage, minimal scopes, rotation |
| Insider threat | Низкая | Критический | RBAC, audit logs, principle of least privilege |
| DDoS | Средняя | Высокий | CDN, rate limiting, auto-scaling |

---

## Multi-tenant Data Isolation

### Принцип: org_id на каждом запросе

```python
# ПРАВИЛЬНО: org_id всегда в WHERE
async def get_missions(self, user_id: UUID, org_id: UUID) -> list[Mission]:
    query = "SELECT * FROM missions WHERE user_id = $1 AND organization_id = $2"
    return await self.pool.fetch(query, user_id, org_id)

# ЗАПРЕЩЕНО: запрос без org_id
async def get_missions(self, user_id: UUID) -> list[Mission]:
    query = "SELECT * FROM missions WHERE user_id = $1"  # SECURITY VIOLATION
```

### Enforcement

- **Service layer:** каждый метод принимает `org_id` как обязательный параметр
- **Route layer:** org_id извлекается из JWT claims или path parameter
- **Tests:** обязательные тесты на cross-tenant isolation (user A org1 не видит данные org2)
- **Code review:** org_id check — mandatory review item для всех PR

### Таблицы с org_id

| Таблица | Сервис | org_id column |
|---------|--------|---------------|
| organizations | Identity | id (сама таблица) |
| org_memberships | Identity | organization_id |
| trust_levels | Identity/Learning | organization_id |
| knowledge_bases | RAG | organization_id |
| documents | RAG | organization_id |
| chunks | RAG | organization_id |
| missions | Learning | organization_id |
| org_subscriptions | Payment | organization_id |

---

## Company Code/Docs Security

### Хранение

- **Embeddings:** pgvector, encrypted at rest (PostgreSQL TDE или disk encryption)
- **Chunk content:** хранится в БД, не в файловой системе
- **Original files:** **не хранятся** после chunking. Только chunks + metadata
- **Content hash:** SHA-256 для dedup, не reversible

### Access controls

- RAG search возвращает только контент из knowledge bases текущей организации
- Chunks содержат `organization_id` — фильтрация на уровне SQL
- Admin API для KB management — только org owner/admin

### Logging

```python
# ЗАПРЕЩЕНО в логах:
logger.info(f"Processing code: {file_content}")  # SECURITY VIOLATION

# ПРАВИЛЬНО:
logger.info(f"Processing document: {document_id}, org: {org_id}, chunks: {chunk_count}")
```

- Никогда не логировать содержимое кода или документов
- Никогда не логировать embeddings
- Логировать только metadata: document_id, org_id, chunk_count, file_path

---

## GitHub Token Management

### Per-org PATs (Personal Access Tokens)

- Каждая организация предоставляет свой GitHub token
- **Minimal scopes:** `repo:read` (только чтение кода)
- **Storage:** encrypted в БД (AES-256), не в env vars
- **Rotation:** admin может обновить token через API
- **Revocation:** при удалении org — token удаляется из БД

### Security measures

- Token используется только в RAG service для clone/pull
- Token не передаётся в другие сервисы
- Token не попадает в логи (masked)
- Webhook secret для auto re-index — отдельный от PAT

---

## LLM Data Governance

### Принцип: минимум контекста в LLM prompt

| Что отправляем | Что НЕ отправляем |
|----------------|-------------------|
| Chunk content (code snippets) | Full file content |
| Concept names and relationships | User personal data |
| Mission structure | GitHub tokens |
| User mastery scores | Email, phone, real names |
| Session telemetry (anonymized) | org_id или user_id в prompt |

### PII masking перед LLM

```python
# Перед отправкой в LLM:
# 1. Убрать email адреса из code comments
# 2. Заменить имена авторов на [AUTHOR]
# 3. Убрать connection strings, API keys из code
# 4. Не включать .env файлы в RAG index
```

### LLM provider compliance

- Gemini: данные не используются для training (API Terms)
- Промпты не хранятся на стороне провайдера (verify per provider)
- При необходимости — self-hosted SLM (Phase Scale)

---

## Trust Level Authorization

### Прогрессивный доступ

```python
# Trust Level проверяется при доступе к ресурсам:
class TrustLevelGuard:
    REQUIRED_LEVELS = {
        "read_docs": 0,          # Newcomer
        "access_dev_env": 1,     # Explorer
        "access_staging": 2,     # Contributor
        "read_prod_repos": 3,    # Builder
        "code_review": 4,        # Guardian
        "full_access": 5,        # Architect
    }
```

### Trust Level не обходится

- Trust Level хранится в БД, не только в JWT
- При повышении — JWT обновляется при следующем refresh
- Admin может вручную повысить/понизить level
- Понижение — только admin action, не автоматическое

---

## Существующие меры безопасности (✅)

| Мера | Статус | Описание |
|------|--------|----------|
| JWT auth | ✅ | Access + refresh tokens, role в claims |
| Bcrypt password hashing | ✅ | Argon2/bcrypt, never plaintext |
| RBAC | ✅ | student, teacher, admin roles |
| Input validation | ✅ | Pydantic models на routes level |
| Parameterized SQL | ✅ | asyncpg, $1/$2 parameters, no concatenation |
| Rate limiting | ✅ | Redis sliding window, 100/min per IP |
| CORS | ✅ | Env-based allowed origins |
| XSS sanitization | ✅ | Bleach for user content |
| JWT refresh rotation | ✅ | Family-based reuse detection |

---

## TODO: Security for B2B

### Sprint 17-20 (Required for pilot)
- [ ] org_id enforcement на всех org-scoped queries
- [ ] Cross-tenant isolation tests (обязательные для каждого endpoint)
- [ ] GitHub token encrypted storage
- [ ] PII masking в LLM prompts
- [ ] Audit logging для admin actions

### Post-launch
- [ ] SOC2 Type II compliance roadmap
- [ ] Penetration testing (третья сторона)
- [ ] Secrets management (Vault / AWS Secrets Manager)
- [ ] mTLS между сервисами
- [ ] Container security hardening
- [ ] Dependency vulnerability scanning (CI)
- [ ] Incident response playbook
