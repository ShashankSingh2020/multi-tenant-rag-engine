<div align="center">

# 🧠 Multi-Tenant Enterprise AI Knowledge Engine

**A multi-tenant Retrieval-Augmented Generation (RAG) SaaS backend with strict workspace isolation, async document ingestion, atomic usage metering, and immutable audit trails.**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.0+-092E20?style=for-the-badge&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.14+-A30000?style=for-the-badge)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-Redis-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4E86F7?style=for-the-badge&logo=google&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

[**Live App**](https://multi-tenant-rag-engine.streamlit.app) · [**API Docs (Swagger)**](https://multi-tenant-rag-engine.onrender.com/api/docs/) · [**Admin**](https://multi-tenant-rag-engine.onrender.com/admin/)

> The demo runs on free-tier hosting, so the first request may take 30–60 seconds while the service wakes up.

</div>

---

## 📑 Table of Contents

- [Why this project](#-why-this-project)
- [Key features](#-key-features)
- [Architecture](#%EF%B8%8F-architecture)
- [How it works](#-how-it-works)
- [Tech stack](#%EF%B8%8F-tech-stack)
- [Data model](#-data-model)
- [Project structure](#-project-structure)
- [Getting started](#-getting-started)
- [Configuration](#%EF%B8%8F-configuration)
- [Running tests](#-running-tests)
- [Security and design decisions](#-security-and-design-decisions)
- [Limitations](#-limitations)
- [Roadmap](#-roadmap)

---

## 🎯 Why this project

Companies want AI search over their private documents, but two things block adoption: **data leaking between customers** and **uncontrolled LLM costs**.

This backend addresses both:

| Problem | How this project handles it |
|---|---|
| One customer seeing another's data | Every query is scoped by organization and project **before** vector similarity ranking runs |
| Slow uploads blocking the API | PDF parsing, chunking, and embedding run in Celery workers, not in the request |
| Over-billing from concurrent requests | Token and request quotas are updated atomically with row locks |
| "Who did what?" questions | Every ingestion, login, and AI query writes an audit record |

---

## ✨ Key features

- 🏢 **Multi-tenancy:** `Organization → Project → Document → DocumentChunk`, with membership-based RBAC
- 🔐 **JWT authentication** and permission checks on every tenant-scoped endpoint
- 📄 **Async ingestion:** upload returns `201 Created` with status `PENDING`; a worker extracts text (PDF/Markdown/text), chunks it, generates embeddings, and flips status to `READY`
- 🔎 **Vector search with pgvector:** 768-dimension embeddings, cosine distance, HNSW index
- 💬 **Grounded answers:** Gemini 2.5 Flash synthesizes responses from retrieved chunks, with source citations and sliding multi-turn context
- 📊 **Usage metering:** per-organization monthly token and request quotas; returns `HTTP 429` when exceeded
- 🧾 **Audit trail:** append-only log of ingestion, authentication, and AI queries with actor and timestamp
- 📚 **OpenAPI docs** via `drf-spectacular`
- 🖥️ **Streamlit dashboard:** workspace switcher, chat, and live quota display

---

## 🏗️ Architecture

```mermaid
flowchart TD
    UI["Streamlit Client<br/>workspace switcher · chat · quota view"]
    API["Django REST Framework<br/>JWT auth · tenant boundary · quota checks"]
    Q["Celery workers<br/>(Redis broker)"]
    RAG["RAG engine<br/>1. scoped filter<br/>2. cosine ranking<br/>3. Gemini synthesis"]
    DB[("PostgreSQL + pgvector<br/>DocumentChunk · UsageRecord · AuditLog")]
    G["Google Gemini API<br/>embeddings + generation"]

    UI -- "HTTPS + JWT" --> API
    API -- "upload → enqueue" --> Q
    API -- "query" --> RAG
    Q -- "extract · chunk · embed" --> G
    Q --> DB
    RAG --> DB
    RAG --> G
```

---

## 🔄 How it works

### Document ingestion (asynchronous)

```mermaid
sequenceDiagram
    participant U as User
    participant A as API
    participant R as Redis
    participant W as Celery worker
    participant D as PostgreSQL
    U->>A: POST document (project scoped)
    A->>D: Save metadata, status = PENDING
    A->>R: Enqueue ingestion task
    A-->>U: 201 Created
    R->>W: Deliver task
    W->>W: Extract text → chunk (300 words, 30 overlap)
    W->>W: Generate Gemini embeddings
    W->>D: Store chunks + vectors, status = READY
```

### Question answering

1. The request is authenticated, and the user's organization membership is verified.
2. The quota is checked and reserved atomically.
3. Chunks are **pre-filtered by organization and project**, then ranked by cosine distance.
4. The top chunks plus recent conversation turns go to Gemini.
5. The answer is returned with the source chunks it was based on, and the event is written to the audit log.

---

## 🛠️ Tech stack

| Layer | Technology | Role |
|---|---|---|
| API | Django 5, Django REST Framework | Business logic, RBAC, JWT auth, REST endpoints |
| Database | PostgreSQL 16 + pgvector | Relational data and vector similarity in one store |
| Async | Celery 5 + Redis | Background document processing |
| AI | Google Gemini (`gemini-2.5-flash`, `text-embedding-004`) | Generation and embeddings |
| UI | Streamlit | Dashboard and chat client |
| Docs | drf-spectacular | OpenAPI 3 schema and Swagger UI |
| Testing | pytest | Automated tests |
| Packaging | Docker, Docker Compose | PostgreSQL (pgvector) and Redis services |

---

## 🗄️ Data model

```mermaid
erDiagram
    ORGANIZATION ||--o{ MEMBERSHIP : has
    ORGANIZATION ||--o{ PROJECT : owns
    PROJECT ||--o{ DOCUMENT : contains
    DOCUMENT ||--o{ DOCUMENTCHUNK : split_into
    ORGANIZATION ||--o{ USAGERECORD : metered_by
    ORGANIZATION ||--o{ AUDITLOG : produces
```

`DocumentChunk` stores the text, a 768-dimension normalized embedding, and foreign keys back to its document, project, and organization, which is what makes the pre-filter possible.

---

## 📂 Project structure

```text
multi-tenant-rag-engine/
├── apps/
│   ├── ai/               # Vector similarity search and Gemini synthesis
│   ├── audit/            # Append-only compliance logging
│   ├── documents/        # Parsing, chunk models, Celery tasks
│   ├── organizations/    # Workspaces and membership RBAC
│   ├── projects/         # Scoped containers for documents
│   └── usage/            # Atomic token tracking and rate limits
├── config/               # Django settings (base/development) and Celery setup
├── scripts/              # Helper scripts
├── tests/                # Test suite
├── frontend_app.py       # Streamlit dashboard
├── docker-compose.yml    # PostgreSQL (pgvector) and Redis
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## 🚀 Getting started

### Prerequisites

- Python 3.11+
- Docker Desktop (recommended) **or** a local PostgreSQL 16 with the `pgvector` extension and Redis
- A [Google Gemini API key](https://aistudio.google.com/)

### 1. Clone and install

```powershell
git clone https://github.com/ShashankSingh2020/multi-tenant-rag-engine.git
cd multi-tenant-rag-engine

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS/Linux, activate with `source venv/bin/activate`.

### 2. Start PostgreSQL (pgvector) and Redis

```powershell
docker compose up -d
```

### 3. Configure environment

```powershell
Copy-Item .env.example .env
```

Then edit `.env` (see [Configuration](#%EF%B8%8F-configuration)).

### 4. Migrate and create an admin user

```powershell
python manage.py migrate
python manage.py createsuperuser
```

### 5. Run the three services (separate terminals)

```powershell
# Terminal 1: API
python manage.py runserver 8000

# Terminal 2: Celery worker (-P solo is required on Windows)
celery -A config worker --loglevel=info -P solo

# Terminal 3: Streamlit UI
streamlit run frontend_app.py
```

Open:

- API docs: http://localhost:8000/api/docs/
- Dashboard: http://localhost:8501

### Try it

1. Register or log in, then create an **Organization** and a **Project**.
2. Upload a document (see `test_knowledge.txt` for a sample).
3. Wait for its status to change from `PENDING` to `READY`.
4. Ask a question in the chat and check the cited sources.

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and set:

| Variable | Description | Example |
|---|---|---|
| `DEBUG` | Django debug mode (use `False` in production) | `True` |
| `SECRET_KEY` | Django secret key | `change-me` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://postgres:password@localhost:5432/multi_tenant_saas` |
| `REDIS_URL` | Celery broker | `redis://127.0.0.1:6379/0` |
| `GEMINI_API_KEY` | Google Gemini API key | `your-key` |

Never commit `.env`.

---

## 🧪 Running tests

```powershell
pytest
```

Tests that touch the database need PostgreSQL running with pgvector.

---

## 🛡️ Security and design decisions

| Decision | Reason |
|---|---|
| Pre-filter vectors by `organization_id` and `project_id` before ranking | Cross-tenant results are impossible by construction, not by post-filtering |
| `select_for_update()` plus `F()` expressions for usage counters | Concurrent requests cannot both pass a quota check and overspend |
| Ingestion in Celery, not in the request | Large PDFs would otherwise block workers and time out |
| Embeddings stored in PostgreSQL (pgvector) | One consistent store, transactional with the metadata |
| Append-only audit records | Supports compliance and debugging |
| Secrets via environment variables | Nothing sensitive in the repo |

---

## ⚠️ Limitations

Being upfront about what this project is and isn't:

- Single-region demo on free-tier hosting; cold starts are expected.
- Retrieval quality depends on the chunking strategy (fixed 300-word windows) and the embedding model; there is no re-ranking step.
- Requires a Gemini API key; there is no offline or mock provider yet.
- Not load-tested at scale. Add your own measurements here once you have them, for example: *p95 query latency on N chunks: ___ ms*.

---

## 🗺️ Roadmap

- [ ] Mock embedding/LLM provider for key-free local runs
- [ ] Automated cross-tenant isolation test in CI
- [ ] Hybrid search (keyword + vector) and re-ranking
- [ ] Benchmarks for ingestion throughput and query latency
- [ ] GitHub Actions CI

---

<div align="center">

Built by **[Shashank Singh](https://github.com/ShashankSingh2020)**

</div>
