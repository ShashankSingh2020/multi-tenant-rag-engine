<div align="center">

# 🧠 Multi-Tenant Enterprise AI Knowledge Engine

### Production-style RAG SaaS with strict tenant isolation, async ingestion & atomic usage metering

[![Django](https://img.shields.io/badge/Django-5.0+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15+-A30000?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL_16-pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4E86F7?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

[**🚀 Live Demo**](https://multi-tenant-rag-engine.streamlit.app) ·
[**📚 API Docs (Swagger)**](https://multi-tenant-rag-engine.onrender.com/api/docs/) ·
[**🛠️ Admin Portal**](https://multi-tenant-rag-engine.onrender.com/admin/)

</div>

---

## 📖 Overview

Companies want AI search over their private documents, but they can't risk **one customer's data leaking into another's answers**, and they can't afford **runaway LLM bills**.

This project is a multi-tenant **Retrieval-Augmented Generation (RAG)** platform that answers those two concerns head-on. Users sign up, create an organization, group documents into projects, and chat with their own knowledge base. Answers come back with the exact source chunks that were used.

| Guarantee | How it is achieved |
| :-- | :-- |
| 🔒 **Tenant isolation** | Every row is scoped `Organization → Project → Document → DocumentChunk`; vector search is pre-filtered by project and org membership *before* similarity ranking. |
| ⚡ **Non-blocking ingestion** | Uploads return `201 Created` immediately; parsing, chunking and embedding run in Celery workers. |
| 💳 **Quota safety** | Token and request counters are updated under PostgreSQL row locks (`select_for_update()` + `F()` expressions), so concurrent requests cannot overspend a plan. |
| 🧾 **Auditability** | Uploads, auth events and AI queries are written to a per-tenant audit trail with actor and timestamp. |

---

## ✨ Features

- 🏢 **Workspaces** – organizations and projects with role-based access (RBAC)
- 📄 **Document ingestion** – PDF, TXT and Markdown with background processing and live `PENDING → READY / FAILED` status
- 🔍 **Semantic search** – 768-dimensional Gemini embeddings stored in PostgreSQL via `pgvector`, ranked by cosine distance
- 💬 **Multi-turn chat** – Gemini 2.5 Flash with sliding conversational context and **cited source chunks** for every answer
- 📊 **Usage metering** – per-organization monthly token, request and document limits; `HTTP 429` when exhausted
- 📋 **Audit logs** – compliance trail of who did what and when
- 🔐 **JWT authentication** – access/refresh tokens via SimpleJWT
- 📘 **OpenAPI 3.0 docs** – auto-generated with `drf-spectacular`
- 🖥️ **Streamlit dashboard** – workspace switcher, chat, document manager, quota telemetry

---

## 🏗️ Architecture

```mermaid
flowchart TD
    UI["🖥️ Streamlit Dashboard<br/>workspace switcher · chat · quotas"]
    API["⚙️ Django REST Framework<br/>JWT auth · RBAC · tenant boundary · quota checks"]
    Q["📬 Celery + Redis<br/>extract · chunk · embed"]
    RAG["🧠 RAG Engine<br/>scoped vector filter → cosine rank → Gemini synthesis"]
    DB[("🐘 PostgreSQL + pgvector<br/>DocumentChunk · UsageRecord · AuditLog")]
    G["✨ Google Gemini<br/>embeddings + generation"]

    UI -- "HTTPS + JWT" --> API
    API -- "upload" --> Q
    API -- "query" --> RAG
    Q --> G
    RAG --> G
    Q --> DB
    RAG --> DB
    API --> DB
```

### 📥 Ingestion flow

```mermaid
sequenceDiagram
    participant U as User
    participant A as Django API
    participant R as Redis
    participant W as Celery Worker
    participant G as Gemini
    participant D as PostgreSQL

    U->>A: POST /documents/project/{id}/ (file)
    A->>D: Save Document (status = PENDING)
    A->>R: Enqueue ingestion task
    A-->>U: 201 Created (PENDING)
    R->>W: Deliver task
    W->>W: Extract text → chunk (300 words, 30 overlap)
    W->>G: Generate embeddings
    W->>D: Store DocumentChunk vectors, status = READY
```

### 💬 Query flow

```mermaid
sequenceDiagram
    participant U as User
    participant A as Django API
    participant D as PostgreSQL
    participant G as Gemini

    U->>A: POST /ai/query/ (project, question, top_k, history)
    A->>D: Check org quota (row lock)
    A->>D: Filter chunks by project + org → cosine rank → top_k
    A->>G: Question + retrieved context + recent history
    G-->>A: Answer + token usage
    A->>D: Atomically record usage + audit entry
    A-->>U: Answer + cited source chunks
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
| :-- | :-- | :-- |
| **API** | Django 5.x, Django REST Framework | Business logic, RBAC, REST endpoints |
| **Auth** | SimpleJWT | Stateless bearer-token authentication |
| **Database** | PostgreSQL 16 + `pgvector` | Relational data and vector similarity in one store |
| **LLM & Embeddings** | Google Gemini (2.5 Flash, 768-d embeddings) | Answer generation and semantic representation |
| **Async jobs** | Celery 5.4+, Redis 7 | Background document processing |
| **Parsing** | `pypdf` | PDF text extraction |
| **Frontend** | Streamlit | Interactive dashboard |
| **API docs** | `drf-spectacular` | OpenAPI schema and Swagger UI |
| **Testing** | `pytest`, `pytest-django` | Automated tests |
| **Infra** | Docker Compose, Gunicorn | Local services and production serving |

---

## 📂 Project Structure

```text
multi-tenant-rag-engine/
├── apps/
│   ├── ai/               # Vector search + Gemini answer synthesis
│   ├── audit/            # Immutable compliance logging
│   ├── documents/        # Parsing, chunk models, Celery ingestion tasks
│   ├── organizations/    # Workspaces and membership RBAC
│   ├── projects/         # Scoped containers for documents
│   └── usage/            # Atomic token/request metering and limits
├── config/               # Django settings and Celery configuration
├── scripts/              # Helper scripts
├── tests/                # Pytest suite
├── frontend_app.py       # Streamlit dashboard
├── docker-compose.yml    # PostgreSQL (pgvector) + Redis
├── Dockerfile
├── manage.py
├── pytest.ini
├── requirements.txt
└── .env.example
```

---

## ⚡ Getting Started

### Prerequisites

- Python **3.11+**
- Docker (recommended) *or* a local PostgreSQL 16 with the `pgvector` extension and Redis
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### 1. Clone and install

```bash
git clone https://github.com/ShashankSingh2020/multi-tenant-rag-engine.git
cd multi-tenant-rag-engine

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start PostgreSQL (pgvector) and Redis

```bash
docker compose up -d
```

This starts `pgvector/pgvector:pg16` on port `5432` (database `multi_tenant_ai_saas`) and Redis 7 on port `6379`.

### 3. Configure environment

```bash
cp .env.example .env
```

Then edit `.env`:

```env
DEBUG=True
SECRET_KEY=change-me
DATABASE_URL=postgres://postgres:postgres@localhost:5432/multi_tenant_ai_saas
REDIS_URL=redis://127.0.0.1:6379/0
GEMINI_API_KEY=your-gemini-api-key
```

### 4. Migrate and create an admin user

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Run the three services

Open three terminals (virtual environment active in each):

```bash
# Terminal 1: API
python manage.py runserver 8000

# Terminal 2: background worker
celery -A config worker --loglevel=info          # add  -P solo  on Windows

# Terminal 3: dashboard (point it at your local API)
API_BASE_URL=http://localhost:8000 streamlit run frontend_app.py
```

> **Windows PowerShell:** `$env:API_BASE_URL="http://localhost:8000"; streamlit run frontend_app.py`
>
> Without `API_BASE_URL`, the dashboard talks to the hosted demo backend.

Open **http://localhost:8501**, register a tenant, create a project, upload a document and start asking questions.

### 6. Run the tests

```bash
pytest
```

---

## 🔌 API at a Glance

Interactive documentation lives at **`/api/docs/`**. Endpoints used by the dashboard:

| Method | Endpoint | Description |
| :-- | :-- | :-- |
| `POST` | `/auth/register/` | Register a new user |
| `POST` | `/auth/login/` | Obtain JWT access token |
| `GET` `POST` | `/organizations/` | List / create organizations |
| `GET` `POST` | `/projects/?organization={id}` | List / create projects |
| `GET` `POST` | `/documents/project/{project_id}/` | List / upload documents (async ingestion) |
| `POST` | `/ai/query/` | RAG query with `project_id`, `query`, `top_k`, `chat_history` |
| `GET` | `/usage/?org_id={id}` | Current plan limits and consumption |
| `GET` | `/audit/?org_id={id}` | Tenant audit trail |

**Example query**

```bash
curl -X POST http://localhost:8000/ai/query/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
        "project_id": 1,
        "query": "What are the main termination clauses?",
        "top_k": 3,
        "chat_history": []
      }'
```

Returns an `answer` plus the `sources` (document title, similarity score, chunk text) that grounded it. Quota exhaustion returns `429 Too Many Requests`.

---

## 🛡️ Security & Compliance Design

- **Tenant boundary at the query layer** – vector search is filtered by `project_id` and org membership before ranking, so other tenants' vectors are never candidates.
- **RBAC** – only members with the right role can view or upload documents in a project.
- **Audit trail** – ingestion, authentication and AI queries are recorded with actor and timestamp.
- **Race-free billing** – row-level locks and database-side `F()` updates keep usage counters correct under concurrency.
- **Secrets via environment** – no keys in source; `.env` is git-ignored.

---

## 🗺️ Roadmap

- [ ] Team management UI: invite members and change roles from the dashboard
- [ ] Token refresh handling in the dashboard
- [ ] Streaming responses for the chat tab
- [ ] Hybrid search (keyword + vector) and re-ranking
- [ ] Full `docker compose` stack (API, worker, dashboard) in one command
- [ ] CI pipeline (tests + lint) with GitHub Actions
- [ ] Per-tenant encryption at rest for document text

---

## 🤝 Contributing

Issues and pull requests are welcome. Please run `pytest` before opening a PR.

---

## 👤 Author

**Shashank Pratap Singh**
[GitHub](https://github.com/ShashankSingh2020) · [LinkedIn](https://linkedin.com/in/shashank-pratap-singh-530437303) · singh2020shashank@gmail.com

<div align="center">

⭐ If this project helped you, consider giving it a star!

</div>

<!--
TODO (optional, big visual upgrade): add screenshots under docs/screenshots/ and embed them here, e.g.
![Chat](docs/screenshots/chat.png)
![Usage dashboard](docs/screenshots/usage.png)
-->
