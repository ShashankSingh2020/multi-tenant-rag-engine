# 🧠 Multi-Tenant Enterprise AI Knowledge Engine (RAG)

[![Django](https://img.shields.io/badge/Django-5.0+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/Django_REST_Framework-3.14+-red?style=for-the-badge)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4E86F7?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Celery](https://img.shields.io/badge/Celery-Distributed_Task_Queue-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI_Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)

A multi-tenant, production-grade Retrieval-Augmented Generation (RAG) platform. Built to deliver sub-second semantic search across private enterprise documents with strict workspace data isolation, asynchronous ingestion pipelines, concurrency-safe token usage metering, and immutable compliance audit trails.

---

## 📌 Executive Summary

Modern enterprises need domain-specific AI search over proprietary documents without risking internal data leakage or uncontrolled API costs. This project implements an enterprise-grade RAG software-as-a-service (SaaS) architecture that guarantees:
- **Zero Cross-Tenant Leakage:** Workspaces, projects, and vector embeddings are strictly partitioned.
- **Asynchronous Processing:** Heavy PDF parsing and vector generation run decoupled from API requests via worker queues.
- **Transactional Quota Protection:** Atomic token and request decrementing prevents race conditions and over-billing.

---

## 🏗️ System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web Client                     │
│    (Workspace Switcher, Multi-Turn Chat, Real-Time Quotas)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JWT Bearer
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Django REST Framework                    │
│   (Tenant Boundary Enforcement, Auth, Quota Validation)     │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
        Document Upload                 Vector Query & Synthesis
               │                               │
               ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│     Celery Task Queue       │ │       RAG Engine Core       │
│      (Redis Broker)         │ │  1. Scoped Vector Filter    │
│  - Text Extraction (PDF/MD) │ │  2. Cosine Distance Rank   │
│  - Semantic Chunking        │ │  3. Gemini 2.5 Synthesis    │
│  - Gemini Embeddings        │ └──────────────┬──────────────┘
└──────────────┬──────────────┘                │
               │                               │
               ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│           PostgreSQL + pgvector Extension                   │
│   - DocumentChunk Table (HNSW/Cosine distance indexing)     │
│   - Tenant Isolation: Pre-filtered by project_id & org_id   │
│   - UsageRecord: select_for_update() atomic token metering  │
└─────────────────────────────────────────────────────────────┘
🚀 Key Architectural & Engineering Highlights1. Strict Tenant Boundary IsolationMulti-tenancy is enforced directly at the database query level across Organization ➔ Project ➔ Document ➔ DocumentChunk.Vector searches perform scoped pre-filtering by project_id and organization membership before running cosine similarity distance rankings, completely preventing cross-tenant vector leakage.2. High-Throughput Asynchronous IngestionDocument ingestion is decoupled from the HTTP request-response cycle using Celery workers and a Redis broker.Upload requests store metadata and return an immediate 201 Created with a PENDING status.Text extraction, chunking (300-word sliding window with 30-word overlap), and Gemini embedding generation happen in the background, updating status to READY upon transaction commit.3. Concurrency-Safe Quota & Metering EngineEnterprise token consumption and query quotas track per organization per monthly billing cycle.Uses PostgreSQL row-level locks (select_for_update()) and database-level F() expressions to prevent race conditions during concurrent user requests.Automatically halts requests with HTTP 429 Too Many Requests when limits are reached.4. Vector Search & LLM OrchestrationVector storage powered by PostgreSQL pgvector storing normalized 768-dimensional embeddings.LLM inference orchestrated with Google's Gemini 2.5 Flash with sliding conversational context and cited source chunk transparency.🛠️ Tech Stack BreakdownDomainTechnologyRole in ArchitectureBackend APIDjango 5.0+, DRFCore business logic, RBAC, JWT authentication, and REST endpointsVector DatabasePostgreSQL 16 + pgvectorRelational data integrity alongside vector similarity searchAI & EmbeddingsGoogle Gemini (gemini-2.5-flash, text-embedding-004)High-speed response generation and vector representationTask QueueCelery 5.3+ & RedisBackground asynchronous document chunking and vector processingFrontend UIStreamlitReactive multi-tab dashboard with real-time quota telemetryAPI DocumentationOpenAPI 3.0 via drf-spectacularSchema generation and interactive API docs📂 Repository LayoutPlaintext├── apps/
│   ├── ai/               # Vector similarity search and Gemini LLM synthesis
│   ├── audit/            # Immutable compliance logging for operations and auth
│   ├── documents/        # PDF/Text parsing, chunk models, and Celery tasks
│   ├── organizations/    # Workspace management and membership RBAC
│   ├── projects/         # Scoped containers for documents and domain knowledge
│   └── usage/            # Atomic token tracking, rate limits, and metering
├── config/               # Django settings (base/development) and Celery setup
├── frontend_app.py       # Streamlit interactive enterprise dashboard
├── docker-compose.yml    # Containerized PostgreSQL (pgvector) and Redis
└── requirements.txt      # Pinned dependency requirements
⚡ Local Setup Guide1. PrerequisitesPython 3.11+PostgreSQL 16+ with pgvector extensionRedis server running on port 6379Google Gemini API Key2. Clone & Virtual EnvironmentBashgit clone [https://github.com/ShashankSingh2020/multi-tenant-rag-engine.git](https://github.com/ShashankSingh2020/multi-tenant-rag-engine.git)
cd multi-tenant-rag-engine

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
3. Configure Environment VariablesCreate a .env file in the root directory:Code snippetDEBUG=True
SECRET_KEY=your-django-secret-key
DATABASE_URL=postgres://postgres:password@localhost:5432/multi_tenant_saas
GEMINI_API_KEY=your-gemini-api-key
REDIS_URL=redis://127.0.0.1:6379/0
4. Apply Database MigrationsBashpython manage.py migrate
5. Launch Development ServicesTerminal 1 (Django Server):Bashpython manage.py runserver 8000
Terminal 2 (Celery Background Worker):Bash# Windows
celery -A config worker --loglevel=info -P solo
Terminal 3 (Streamlit UI):Bashstreamlit run frontend_app.py
🛡️ Enterprise Security & ComplianceStrict RBAC: Only organization members with appropriate permissions can view or upload documents to a project.Audit Logging: Every document ingestion, authentication attempt, and AI query creates an immutable audit trail with actor details and timestamps.Vector Isolation: All vectors reside strictly within PostgreSQL tables bounded by organization and project foreign keys.