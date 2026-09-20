# 🧠 Multi-Tenant Enterprise AI Knowledge Engine (RAG)

[![Django](https://img.shields.io/badge/Django-5.1-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-red?style=for-the-badge)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-Embeddings_%26_Flash-4E86F7?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Celery](https://img.shields.io/badge/Celery-Distributed_Task_Queue-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Pytest](https://img.shields.io/badge/Tests-23%2F23%20Passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)

A multi-tenant, production-ready Retrieval-Augmented Generation (RAG) SaaS platform. Delivers sub-second semantic search across private enterprise documents with absolute workspace data isolation, asynchronous ingestion queues, cryptographically secure team invitation workflows, concurrency-safe token usage metering, and immutable audit trails.

---

## 📌 Executive Summary

Modern SaaS architectures require domain-specific AI search over proprietary documents without risking cross-tenant data leakage or runaway API costs. This platform solves these production concerns with four operational guarantees:

- **Zero Cross-Tenant Leakage:** Organizations, projects, documents, and vector embeddings are partitioned at the database query level with strict composite foreign-key scoping.
- **Role-Based Access & Secure Invitations:** Cryptographically signed, time-expiring invitation tokens enforce strict RBAC (`OWNER`, `ADMIN`, `MEMBER`) without privilege escalation vectors.
- **Asynchronous Ingestion Pipelines:** Text extraction, semantic sliding-window chunking, and embedding generation are decoupled from API cycles via Celery workers backed by Redis.
- **Concurrency-Safe Quota Protection:** Atomic token and request decrementing via row-level database locks (`select_for_update`) prevent race conditions and over-billing.

---

## 🏗️ System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                           │
│        (Frontend UI / Third-Party REST API Consumers)       │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JWT Bearer Tokens
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Django REST Framework                    │
│   - Multi-Tenant Boundary Scoping (Org / Project Isolation) │
│   - Cryptographic Team Invitations & RBAC Checks            │
│   - Concurrency-Safe Quota & Throttling Enforcement         │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
        Document Upload                  Vector Query & Synthesis
               │                               │
               ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│      Celery Task Queue      │ │       RAG Engine Core       │
│        (Redis Broker)       │ │  1. Scoped Vector Pre-filter│
│  - Text Extraction (PDF/TXT)│ │  2. Cosine Similarity Rank  │
│  - Chunking (300w / 30 ovr) │ │  3. Gemini Flash Synthesis  │
│  - Gemini Vector Generation │ └──────────────┬──────────────┘
└──────────────┬──────────────┘                │
               │                               │
               ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL 16 + pgvector Extension             │
│  - DocumentChunk: 768-dim embeddings with HNSW cosine index │
│  - Tenant Isolation: Scoped by org_id and project_id        │
│  - UsageRecord: select_for_update() atomic metering         │
│  - AuditLog: Automated Django signals on sensitive events   │
└─────────────────────────────────────────────────────────────┘
🚀 Key Engineering & Production Features1. Strict Multi-Tenant Data IsolationTenant hierarchies follow a deterministic chain: Organization ➔ Project ➔ Document ➔ DocumentChunk.Vector searches execute scoped pre-filtering on project_id and caller membership before running vector cosine distance calculations. This eliminates cross-tenant data leakage inside the vector space.2. Team Invitations & Cryptographic RBACSecure team invitation engine utilizing cryptographically randomized URL-safe tokens (secrets.token_urlsafe(32)).7-day automated expiration with status state-machine transitions (PENDING ➔ ACCEPTED / REVOKED).RBAC permission barriers (OWNER, ADMIN, MEMBER) prevent unauthorized members from managing billing, issuing invites, or viewing compliance audit logs.3. Decoupled Ingestion & Vector PipelineFile upload returns an immediate 201 Created with a PENDING state, preventing slow I/O blocking on web server workers.Celery workers parse files asynchronously, perform sliding-window chunking (300 words with 30-word overlap for context preservation), generate normalized 768-dimensional embeddings via Gemini, and atomically commit records to PostgreSQL.4. Concurrency-Safe Quota MeteringReal-time tracking of token counts, AI request counts, and document quotas per organization billing cycle.Implemented with PostgreSQL row-level locks (select_for_update()) and database F() expressions to prevent concurrency race conditions under heavy traffic.5. Automated Compliance Audit TrailsSignal-driven audit logging capturing IP addresses, actors, and events (AUTH_LOGIN, DOCUMENT_UPLOAD, AI_QUERY, INVITATION_SENT).Audit logs are strictly restricted to organization OWNER roles.🛠️ Tech StackLayerTechnologyPurposeBackend FrameworkDjango 5.1 & Django REST FrameworkCore APIs, database ORM, RBAC, and business logicDatabase & VectorsPostgreSQL 16 + pgvectorRelational integrity + HNSW cosine vector index (768-dim)AI OrchestrationGoogle Gemini API (text-embedding-004, gemini-2.5-flash)Semantic embeddings and contextual RAG response synthesisAsync Task EngineCelery 5.4 + Redis 7Distributed asynchronous document parsing and ingestionAPI DocumentationOpenAPI 3.0 via drf-spectacularInteractive Swagger UI documentation with JWT supportTestingPytest + Pytest-DjangoComprehensive 23-test suite covering isolation, auth, and RAG📂 Repository StructurePlaintext├── apps/
│   ├── accounts/         # Custom User model, JWT authentication, and signals
│   ├── ai/               # RAG similarity retrieval & Gemini LLM synthesis
│   ├── audit/            # Compliance audit logging via automated Django signals
│   ├── common/           # Abstract TimeStampedUUIDModel, throttling & utilities
│   ├── documents/        # PDF/text ingestion, chunking models, and Celery tasks
│   ├── organizations/    # Multi-tenancy, RBAC membership, and invitation engine
│   ├── projects/         # Scoped containers for documents and domain knowledge
│   ├── subscriptions/    # Tier limits, subscription plans, and seat definitions
│   └── usage/            # Atomic select_for_update() token metering & quotas
├── config/               # Project configuration, Celery setup, base/dev settings
├── tests/                # 23 automated integration & isolation test cases
├── docker-compose.yml    # PostgreSQL with pgvector and Redis infrastructure
└── requirements.txt      # Pinned dependency requirements
⚡ Local Setup Guide1. PrerequisitesPython 3.11+Docker & Docker Compose (for PostgreSQL + pgvector and Redis)Google Gemini API Key2. Infrastructure SetupStart the containerized PostgreSQL (with pgvector) and Redis broker:Bashdocker compose up -d
3. Environment ConfigurationCreate a .env file in the root directory:Code snippetDEBUG=True
SECRET_KEY=your-super-secret-django-key
DATABASE_URL=postgres://postgres:postgres@localhost:5432/multi_tenant_ai_saas
REDIS_URL=redis://127.0.0.1:6379/1
GEMINI_API_KEY=your-gemini-api-key
4. Installation & Database SetupBash# Create and activate virtual environment
python -m venv venv
venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create a superuser for the admin portal
python manage.py createsuperuser
5. Start Application ServicesTerminal 1: Django API ServerBashpython manage.py runserver 8000
Terminal 2: Celery Background Ingestion WorkerBash# Windows
celery -A config worker --loglevel=info -P solo

# Linux / macOS
celery -A config worker --loglevel=info
🧪 Automated Testing SuiteThe application includes an automated test suite verifying multi-tenant isolation, RBAC barriers, task pipelines, and vector cosine distance lookups:Bashpytest
Plaintexttests/test_audit_logging.py ...... PASSED
tests/test_auth.py ............. PASSED
tests/test_ingestion_vectors.py .. PASSED
tests/test_invitations.py ........ PASSED
tests/test_organizations.py ...... PASSED
tests/test_projects_documents.py . PASSED
tests/test_tenant_isolation.py ... PASSED
====================== 23 passed in 21.66s ======================
💬 System Design & Technical Interview TopicsKey architectural talking points when explaining this project in engineering interviews:1. Why pgvector instead of a standalone vector database like Pinecone?"Using pgvector eliminates the dual-write problem and cross-system synchronization lag. With PostgreSQL, transactional document updates, metadata scoping, relational user permissions, and vector similarity search occur within a single ACID-compliant database. We filter vectors on org_id and project_id before computing cosine distance, minimizing search space and preventing tenant leakage."2. How are concurrent requests prevented from exceeding token quotas?"Token accounting uses PostgreSQL row-level locks via select_for_update(). When a query or document upload initiates, the active UsageRecord row for the tenant is locked inside a transaction.atomic() block. Any concurrent requests wait until the transaction commits, preventing race conditions that lead to quota bypass."3. Why decouple document ingestion with Celery?"Parsing large text documents, executing sliding-window chunking, and calling external embedding APIs introduces variable latency (2–10+ seconds). Offloading this work to Celery workers with a Redis broker keeps API response times fast (sub-50ms), provides automatic retries on rate limits, and prevents worker starvation on the main web server."

## 🚀 Live Demo & Documentation

* **Live Application UI:** [https://multi-tenant-rag-engine.streamlit.app](https://multi-tenant-rag-engine.streamlit.app)
* **Interactive API Docs (Swagger):** [https://multi-tenant-rag-engine.onrender.com/api/docs/](https://multi-tenant-rag-engine.onrender.com/api/docs/)
* **Django Admin Portal:** [https://multi-tenant-rag-engine.onrender.com/admin/](https://multi-tenant-rag-engine.onrender.com/admin/)
