<div align="center">

# 🧠 Multi-Tenant Enterprise AI Knowledge Engine

### A RAG (Retrieval-Augmented Generation) SaaS backend where every company gets its own private, quota-controlled, fully audited AI search over its own documents.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.0+-092E20?style=for-the-badge&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.14+-A30000?style=for-the-badge)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL_16-pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-Redis-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4E86F7?style=for-the-badge&logo=google&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

[**🚀 Live App**](https://multi-tenant-rag-engine.streamlit.app) &nbsp;·&nbsp; [**📘 API Docs (Swagger)**](https://multi-tenant-rag-engine.onrender.com/api/docs/) &nbsp;·&nbsp; [**🛠 Admin Portal**](https://multi-tenant-rag-engine.onrender.com/admin/)

> ⏳ The demo runs on free-tier hosting. If it has been idle, the first request can take 30–60 seconds while the service wakes up.

</div>

---

## 📑 Table of Contents

1. [What is this project?](#1--what-is-this-project)
2. [The problem it solves](#2--the-problem-it-solves)
3. [Features](#3--features)
4. [Quick tour: what a user can do](#4--quick-tour-what-a-user-can-do)
5. [System architecture](#5-%EF%B8%8F-system-architecture)
6. [How it works, step by step](#6--how-it-works-step-by-step)
7. [Multi-tenancy and data isolation](#7--multi-tenancy-and-data-isolation)
8. [Usage metering and quotas](#8--usage-metering-and-quotas)
9. [Audit logging](#9--audit-logging)
10. [Authentication and access control](#10--authentication-and-access-control)
11. [Data model](#11--data-model)
12. [API overview](#12--api-overview)
13. [Code structure (module by module)](#13--code-structure-module-by-module)
14. [Technology choices and why](#14-%EF%B8%8F-technology-choices-and-why)
15. [Getting started](#15--getting-started)
16. [Configuration reference](#16-%EF%B8%8F-configuration-reference)
17. [Deployment](#17--deployment)
18. [Testing](#18--testing)
19. [Security notes](#19-%EF%B8%8F-security-notes)
20. [Performance notes](#20--performance-notes)
21. [Troubleshooting](#21--troubleshooting)
22. [Limitations](#22-%EF%B8%8F-limitations)
23. [Roadmap](#23-%EF%B8%8F-roadmap)
24. [Author](#24--author)

> **Note on accuracy:** sections marked **🔎 Verify** describe behaviour that follows from the design above but whose exact names (fields, URLs, status values) should be checked against the code before publishing. The live Swagger docs are always the source of truth for endpoints.

---

## 1. 🎯 What is this project?

**Multi-Tenant Enterprise AI Knowledge Engine** is a backend platform that lets many organizations (tenants) upload their private documents and ask questions about them in natural language. The system finds the most relevant passages in *that organization's own documents only*, hands them to a Large Language Model (Google Gemini), and returns an answer with **citations** pointing back to the source passages.

This pattern is called **Retrieval-Augmented Generation (RAG)**:

```text
Question ──► find relevant chunks in YOUR documents ──► give chunks + question to the LLM ──► grounded answer + sources
```

What makes this project different from a typical "chat with your PDF" demo is that it is built like a **SaaS product**:

- many organizations share one deployment, but **cannot see each other's data**,
- heavy work (parsing, chunking, embedding) happens **in the background**,
- every organization has **usage quotas** that stay correct even under concurrent requests,
- every sensitive action leaves an **audit record**.

It ships with a Django REST API, a Celery worker pipeline, a PostgreSQL + pgvector data layer, and a Streamlit dashboard.

---

## 2. 🧩 The problem it solves

Companies want AI search over internal documents (policies, contracts, manuals, reports), but four things stop them:

| Concern | Why it matters | How this project responds |
|---|---|---|
| **Data leakage between customers** | One company's confidential file must never appear in another's answer | Every vector search is filtered by organization and project **before** similarity ranking |
| **Slow, blocking uploads** | Parsing a large PDF and generating embeddings can take a long time | Ingestion runs in Celery workers; the API returns immediately |
| **Runaway LLM cost** | Concurrent users can overspend a plan if counters race | Quotas updated with row-level locks and atomic database expressions |
| **Accountability** | Admins need to know who uploaded or asked what | Append-only audit log of ingestion, authentication, and AI queries |

---

## 3. ✨ Features

### Multi-tenant SaaS foundation
- **Organization → Project → Document → Chunk** hierarchy
- Membership-based **role-based access control (RBAC)**
- **JWT bearer authentication**

### Document ingestion
- Supports **PDF, Markdown, and plain-text** documents
- **Asynchronous pipeline** (upload → background extraction → chunking → embedding → ready)
- Immediate `201 Created` response with a `PENDING` status
- **Sliding-window chunking:** 300 words per chunk with 30 words of overlap, so sentences at chunk boundaries are not lost

### Retrieval and generation
- **768-dimension normalized embeddings** (Gemini `text-embedding-004`) stored in PostgreSQL with **pgvector**
- **Cosine-distance** similarity with an **HNSW** index
- **Gemini 2.5 Flash** answer synthesis with **source citations**
- **Multi-turn conversation** using a sliding window of recent messages

### Governance
- **Per-organization monthly quotas** for tokens and requests
- `HTTP 429 Too Many Requests` when a quota is exhausted
- **Immutable audit trail** with actor and timestamp

### Developer experience
- **OpenAPI 3** schema and Swagger UI via `drf-spectacular`
- **Streamlit dashboard:** workspace switcher, chat, live quota telemetry
- **Docker Compose** for PostgreSQL (pgvector) and Redis
- **pytest** test suite

---

## 4. 🧭 Quick tour: what a user can do

1. **Sign up / log in** and receive a JWT.
2. **Create or join an organization** (a workspace for a company or team).
3. **Create a project** inside the organization (e.g., "HR Policies", "Product Manuals").
4. **Upload documents** to the project. Each document shows `PENDING` and becomes `READY` when processing finishes.
5. **Ask questions** in the chat. The answer cites the exact chunks it used.
6. **Watch usage**: the dashboard shows how much of the monthly token/request quota is left.
7. **Admins** review the audit trail.

> 📸 *Add screenshots here: the workspace switcher, the document list with statuses, the chat with citations, and the quota panel. Store images in a `docs/` folder and reference them, e.g. `![Chat](docs/chat.png)`.*

---

## 5. 🏗️ System architecture

```mermaid
flowchart TD
    UI["🖥️ Streamlit Client<br/>workspace switcher · multi-turn chat · quota telemetry"]
    API["⚙️ Django REST Framework<br/>JWT auth · tenant boundary · quota validation"]
    Q["📬 Celery workers<br/>Redis broker"]
    RAG["🔎 RAG engine core<br/>1. scoped filter<br/>2. cosine ranking<br/>3. Gemini synthesis"]
    DB[("🗄️ PostgreSQL + pgvector<br/>Documents · Chunks (HNSW) · UsageRecord · AuditLog")]
    G["✨ Google Gemini API<br/>embeddings + generation"]

    UI -- "HTTPS + JWT Bearer" --> API
    API -- "upload → enqueue task" --> Q
    API -- "question" --> RAG
    Q -- "extract · chunk · embed" --> G
    Q -- "store chunks + vectors" --> DB
    RAG -- "scoped vector search" --> DB
    RAG -- "prompt with context" --> G
```

### Component responsibilities

| Component | Responsibility |
|---|---|
| **Streamlit client** | User interface: login, workspace switching, upload, chat, quota display |
| **Django REST Framework** | Authentication, permission checks, tenant boundary enforcement, quota checks, REST endpoints |
| **Redis** | Message broker that carries ingestion tasks to workers |
| **Celery worker** | Text extraction, chunking, embedding generation, status updates |
| **RAG engine (`apps/ai`)** | Scoped vector search, context assembly, calling Gemini, returning citations |
| **PostgreSQL + pgvector** | Relational data, vectors, usage counters, and audit records in one transactional store |
| **Gemini API** | Embeddings for chunks/questions and answer generation |

---

## 6. 🔄 How it works, step by step

### 6.1 Document ingestion (asynchronous)

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant A as Django API
    participant D as PostgreSQL
    participant R as Redis
    participant W as Celery worker
    participant G as Gemini

    U->>A: Upload document to a project (JWT)
    A->>A: Authenticate, verify org membership + project scope
    A->>D: Save document metadata, status = PENDING
    A->>R: Enqueue ingestion task
    A-->>U: 201 Created (status PENDING)
    R->>W: Deliver task
    W->>W: Extract text (PDF / Markdown / text)
    W->>W: Split into 300-word chunks, 30-word overlap
    W->>G: Generate embeddings (768 dimensions)
    G-->>W: Vectors
    W->>D: Store chunks + normalized vectors
    W->>D: Set status = READY
    W->>D: Write audit record
```

**Why chunking with overlap?** Embedding a whole document would blur its meaning, and splitting without overlap can cut a sentence in half. A 300-word window with a 30-word overlap keeps each chunk focused while preserving context across boundaries.

**Example.** A 700-word document produces chunks covering words 1–300, 271–570, and 541–700, so each boundary is covered twice.

> 🔎 **Verify:** If your pipeline marks failed documents (for example `FAILED`) and records an error message, document that here. Describe what happens when extraction or the Gemini call fails.

### 6.2 Answering a question

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant A as Django API
    participant Q as Usage / quota
    participant V as pgvector search
    participant G as Gemini

    U->>A: Ask a question in a project (JWT)
    A->>A: Authenticate + verify org membership
    A->>Q: Check and reserve quota (atomic)
    Q-->>A: OK (or 429 if exhausted)
    A->>G: Embed the question
    G-->>A: Query vector
    A->>V: Pre-filter by organization + project, rank by cosine distance
    V-->>A: Top-K chunks
    A->>G: Prompt = recent conversation + chunks + question
    G-->>A: Answer
    A->>Q: Record actual token usage
    A->>A: Write audit record
    A-->>U: Answer + cited source chunks
```

**Order matters:** the tenant filter runs **before** similarity ranking. Chunks from other organizations are never candidates, so they cannot be retrieved by accident or by a clever prompt.

### 6.3 Conversation context

Follow-up questions ("and what about contractors?") only make sense with earlier turns. The engine keeps a **sliding window** of recent messages and includes it in the prompt, so the conversation stays coherent without growing the prompt indefinitely.

---

## 7. 🏢 Multi-tenancy and data isolation

### The hierarchy

```mermaid
flowchart LR
    O["Organization<br/>(tenant)"] --> P["Project"]
    P --> D["Document"]
    D --> C["DocumentChunk<br/>text + vector"]
    O --> M["Membership<br/>(user + role)"]
```

Every `DocumentChunk` can be traced up to a project and an organization through foreign keys. That is what makes tenant filtering possible at the database level.

### Where isolation is enforced

| Layer | Mechanism |
|---|---|
| **Authentication** | JWT identifies the user |
| **Authorization** | Membership check: is this user in this organization with a role that allows the action? |
| **Query scoping** | Vector search is filtered by `project_id` and organization membership before ranking |
| **Quotas** | Counted per organization, so one tenant cannot consume another's allowance |
| **Audit** | Records carry actor and organization context |

### Why filter *before* ranking?

If you rank all chunks first and filter afterwards, other tenants' data has already been touched and could leak through bugs or limits (for example, top-K filled entirely by other tenants' chunks, leaving the real tenant with no results). Filtering first guarantees that results can only come from the caller's own project.

### Illustrative query shape

```python
# Illustrative only: the actual implementation lives in apps/ai
chunks = (
    DocumentChunk.objects
    .filter(project_id=project.id, project__organization__memberships__user=request.user)
    .annotate(distance=CosineDistance("embedding", query_vector))
    .order_by("distance")[:TOP_K]
)
```

> 🔎 **Verify:** replace the snippet with the real query from `apps/ai`, or remove it.

### How to prove it

Add an automated test that creates two organizations with similar documents, queries as organization A, and asserts that no chunk from organization B is ever returned. This is the strongest evidence for the isolation claim.

---

## 8. 📊 Usage metering and quotas

Each organization has a **monthly billing cycle** with limits on **tokens** and **requests**.

### The race condition this solves

Suppose an organization has **100 tokens** left and two requests arrive at the same moment, each needing 80:

```text
Without locking:                       With row lock + atomic update:
 Request A reads: 100 left → OK         Request A locks the usage row, reads 100 → OK, writes 20
 Request B reads: 100 left → OK         Request B waits, then reads 20 → rejected (429)
 Both proceed → 160 used of 100 ❌       Total stays within the limit ✅
```

### How it is implemented

- **`select_for_update()`** locks the organization's usage row inside a transaction so concurrent requests are serialized.
- **`F()` expressions** perform the increment inside the database (`tokens_used = tokens_used + n`) rather than read-modify-write in Python.
- When the limit is reached, the API returns **`429 Too Many Requests`**.

### What the user sees

The Streamlit dashboard shows live quota telemetry: tokens used vs. allowed and requests used vs. allowed for the current cycle.

> 🔎 **Verify:** describe when the cycle resets (calendar month vs. rolling 30 days) and whether quota is reserved before the LLM call and adjusted afterwards, or recorded after.

---

## 9. 🧾 Audit logging

The `audit` app records an **append-only** trail of important events:

| Event | Example information captured |
|---|---|
| Authentication | Login attempts, success or failure |
| Document ingestion | Who uploaded what, to which project, when |
| AI queries | Who asked, in which project, when |

Each record has an **actor** and a **timestamp**. Records are never edited by the application, which supports compliance reviews and debugging ("who uploaded this document?", "who queried the finance project last week?").

---

## 10. 🔐 Authentication and access control

- **Authentication:** JWT bearer tokens (`Authorization: Bearer <token>`).
- **Authorization:** DRF permission classes check organization membership and role on every tenant-scoped endpoint.
- **Roles:** membership carries a role that determines what the user may do (for example upload vs. read-only).

> 🔎 **Verify:** list your actual roles and what each can do, for example in a table:
>
> | Role | Can read / ask | Can upload | Can manage members |
> |---|---|---|---|
> | Owner / Admin | ✅ | ✅ | ✅ |
> | Member | ✅ | ✅ | ❌ |
> | Viewer | ✅ | ❌ | ❌ |

---

## 11. 🗄️ Data model

```mermaid
erDiagram
    USER ||--o{ MEMBERSHIP : has
    ORGANIZATION ||--o{ MEMBERSHIP : includes
    ORGANIZATION ||--o{ PROJECT : owns
    PROJECT ||--o{ DOCUMENT : contains
    DOCUMENT ||--o{ DOCUMENTCHUNK : "split into"
    ORGANIZATION ||--o{ USAGERECORD : "metered by"
    USER ||--o{ AUDITLOG : "acts in"
```

| Model | Purpose |
|---|---|
| `Organization` | The tenant; owns projects, members, and a usage allowance |
| `Membership` | Links a user to an organization with a role |
| `Project` | A scoped container for related documents |
| `Document` | An uploaded file with metadata and a processing status |
| `DocumentChunk` | A piece of text with its 768-dimension embedding; indexed with HNSW |
| `UsageRecord` | Per-organization, per-billing-cycle token and request counters |
| `AuditLog` | Immutable record of actions with actor and timestamp |

> 🔎 **Verify:** field names and exact model names against `apps/*/models.py`.

---

## 12. 📡 API overview

The complete, always-current reference is the interactive Swagger UI:

👉 **https://multi-tenant-rag-engine.onrender.com/api/docs/** (locally: `http://localhost:8000/api/docs/`)

Typical groups of endpoints:

| Area | What it does |
|---|---|
| **Auth** | Register, log in, refresh tokens |
| **Organizations** | Create and list workspaces, manage membership |
| **Projects** | Create and list projects inside an organization |
| **Documents** | Upload, list, check processing status |
| **AI / Query** | Ask a question, receive an answer with citations |
| **Usage** | View current quota and consumption |
| **Audit** | View audit records (privileged roles) |

### Example (PowerShell, illustrative)

```powershell
# 1. Log in and keep the token  (adjust the path to match your Swagger docs)
$login = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/auth/login/" `
  -ContentType "application/json" `
  -Body '{"email":"you@example.com","password":"your-password"}'
$token = $login.access

# 2. Ask a question in a project
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/ai/query/" `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body '{"project_id": 1, "question": "What is the leave policy?"}'
```

> 🔎 **Verify:** URL paths and request bodies against Swagger before publishing, or delete the examples.

### Example response shape (illustrative)

```json
{
  "answer": "Employees receive ... [Source 1]",
  "sources": [
    { "document": "hr-policy.pdf", "chunk_index": 12, "excerpt": "…" }
  ],
  "usage": { "tokens": 812 }
}
```

---

## 13. 🧱 Code structure (module by module)

```text
multi-tenant-rag-engine/
├── apps/
│   ├── ai/               # Vector similarity search + Gemini synthesis (the RAG core)
│   ├── audit/            # Immutable compliance logging for operations and auth
│   ├── documents/        # PDF/text parsing, chunk models, Celery ingestion tasks
│   ├── organizations/    # Workspaces, membership, role-based access
│   ├── projects/         # Scoped containers for documents
│   └── usage/            # Atomic token tracking, rate limits, metering
├── config/               # Django settings (base / development) and Celery setup
├── scripts/              # Helper scripts
├── tests/                # pytest suite
├── frontend_app.py       # Streamlit dashboard
├── docker-compose.yml    # PostgreSQL (pgvector) and Redis
├── Dockerfile
├── manage.py
├── pytest.ini
├── requirements.txt
├── .env.example
└── test_knowledge.txt    # Sample document for trying the system
```

| App | Responsibility in one line |
|---|---|
| `organizations` | Who belongs to which tenant, and with what role |
| `projects` | Groups documents inside a tenant |
| `documents` | Stores uploads and turns them into searchable chunks (Celery) |
| `ai` | Finds relevant chunks and asks Gemini to answer using them |
| `usage` | Counts tokens/requests and enforces quotas atomically |
| `audit` | Records who did what and when |

---

## 14. 🛠️ Technology choices and why

| Technology | Why it was chosen |
|---|---|
| **Django + DRF** | Mature ORM, migrations, auth ecosystem, and fast REST development |
| **PostgreSQL + pgvector** | Keeps vectors next to relational data, so tenant filters and transactions work naturally without a separate vector database |
| **HNSW index** | Fast approximate nearest-neighbour search on cosine distance |
| **Celery + Redis** | Reliable background processing for slow ingestion work |
| **Gemini 2.5 Flash / text-embedding-004** | Fast generation and 768-dimension embeddings |
| **drf-spectacular** | Automatic OpenAPI schema and Swagger UI |
| **Streamlit** | Quick interactive dashboard without a separate frontend build |
| **Docker Compose** | One command for PostgreSQL (with pgvector) and Redis |

---

## 15. 🚀 Getting started

### Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | |
| Docker Desktop | Easiest way to get PostgreSQL with pgvector and Redis |
| Google Gemini API key | Create one at https://aistudio.google.com/ |
| Git | |

### Step 1: Clone and install

```powershell
git clone https://github.com/ShashankSingh2020/multi-tenant-rag-engine.git
cd multi-tenant-rag-engine

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> macOS/Linux: activate with `source venv/bin/activate`.

### Step 2: Start PostgreSQL (pgvector) and Redis

```powershell
docker compose up -d
```

Without Docker you need PostgreSQL 16 with the `pgvector` extension installed and Redis running on port 6379.

### Step 3: Configure environment variables

```powershell
Copy-Item .env.example .env
```

Edit `.env` (see the [configuration reference](#16-%EF%B8%8F-configuration-reference)).

### Step 4: Apply migrations and create an admin

```powershell
python manage.py migrate
python manage.py createsuperuser
```

### Step 5: Run the three processes (three terminals)

```powershell
# Terminal 1: Django API
python manage.py runserver 8000
```

```powershell
# Terminal 2: Celery worker  (-P solo is needed on Windows)
celery -A config worker --loglevel=info -P solo
```

```powershell
# Terminal 3: Streamlit dashboard
streamlit run frontend_app.py
```

### Step 6: Open the app

| What | URL |
|---|---|
| Swagger API docs | http://localhost:8000/api/docs/ |
| Django admin | http://localhost:8000/admin/ |
| Streamlit dashboard | http://localhost:8501 |

### Step 7: Try the full flow

1. Register or log in.
2. Create an organization and a project.
3. Upload `test_knowledge.txt` (included as a sample).
4. Wait until the document status becomes `READY`.
5. Ask a question about its content and check the citations.
6. Open the quota panel and confirm usage increased.

---

## 16. ⚙️ Configuration reference

Create `.env` in the project root (never commit it).

| Variable | Required | Description | Example |
|---|---|---|---|
| `DEBUG` | Yes | Django debug mode; **must be `False` in production** | `True` |
| `SECRET_KEY` | Yes | Django secret key; use a long random value | `change-me` |
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgres://postgres:password@localhost:5432/multi_tenant_saas` |
| `REDIS_URL` | Yes | Celery broker URL | `redis://127.0.0.1:6379/0` |
| `GEMINI_API_KEY` | Yes | Google Gemini API key | `your-gemini-api-key` |

---

## 17. ☁️ Deployment

The public demo uses free tiers:

| Part | Host |
|---|---|
| Django API + Swagger + Admin | Render |
| Streamlit dashboard | Streamlit Community Cloud |

Production checklist:

- [ ] `DEBUG=False`, strong `SECRET_KEY`, correct `ALLOWED_HOSTS`
- [ ] Managed PostgreSQL with the `pgvector` extension enabled
- [ ] Managed Redis for Celery
- [ ] At least one Celery worker running alongside the web service
- [ ] Secrets set as environment variables on the host, not in the repo
- [ ] HTTPS enabled and CORS restricted to the dashboard origin

> Free tiers sleep when idle, so the first request after inactivity is slow.

---

## 18. 🧪 Testing

```powershell
pytest
```

Configuration lives in `pytest.ini`. Tests that touch the database require PostgreSQL (with pgvector) to be running.

Suggested coverage to maintain:

- tenant isolation (user from org A can never retrieve org B's chunks),
- quota enforcement under concurrent requests,
- ingestion status transitions,
- permission checks per role.

---

## 19. 🛡️ Security notes

| Topic | Approach |
|---|---|
| Tenant isolation | Pre-filtered vector search by organization/project |
| Authentication | JWT bearer tokens |
| Authorization | Membership and role checks in DRF permissions |
| Secrets | Environment variables only; `.env` is git-ignored |
| Abuse and cost control | Per-organization quotas with `429` responses |
| Traceability | Append-only audit records |
| Data sent to a third party | Document text and questions are sent to the Gemini API; users should be informed that Google's data policies apply |

---

## 20. ⚡ Performance notes

- **HNSW** gives fast approximate search; it trades a little recall for much lower latency than an exact scan.
- **Filtering first** keeps the candidate set small and relevant.
- **Chunk size** is a trade-off: smaller chunks are more precise but lose context; larger chunks keep context but dilute relevance.
- **Embedding at ingestion time** keeps query latency low, since only the question needs embedding at query time.

> 📏 *Add your own measurements here, for example: "p95 query latency over N chunks: ___ ms; ingestion throughput: ___ pages/min." Replace this note with real numbers, or leave performance claims out.*

---

## 21. 🩹 Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `extension "vector" is not available` | PostgreSQL without pgvector | Use the Docker image from `docker-compose.yml` or install pgvector, then run `CREATE EXTENSION vector;` |
| Documents stay `PENDING` | Celery worker not running, or Redis unreachable | Start the worker and check `REDIS_URL` |
| Celery crashes on Windows | Default pool unsupported | Run with `-P solo` |
| `401 Unauthorized` | Missing or expired token | Log in again and send `Authorization: Bearer <token>` |
| `429 Too Many Requests` | Monthly quota reached | Check the usage panel or reset the allowance in admin |
| Gemini errors / empty answers | Invalid or exhausted API key | Verify `GEMINI_API_KEY` and quota in Google AI Studio |
| First request very slow on the demo | Free-tier cold start | Wait 30–60 seconds and retry |

---

## 22. ⚠️ Limitations

- Retrieval quality depends on fixed-size chunking and the embedding model; there is no re-ranking step.
- Requires a Gemini API key; there is no offline or mock provider yet.
- Scanned (image-only) PDFs need OCR, which is not included.
- Demo hosting is free-tier and not sized for heavy load.
- Document text is processed by an external API (Gemini).

---

## 23. 🗺️ Roadmap

- [ ] Mock embedding/LLM provider so the project runs without an API key
- [ ] Automated cross-tenant isolation test in CI
- [ ] Hybrid search (keyword + vector) with re-ranking
- [ ] Benchmarks for ingestion throughput and query latency
- [ ] GitHub Actions CI
- [ ] OCR for scanned documents
- [ ] Per-user usage reporting and exportable audit logs

---

## 24. 👤 Author

**Shashank Singh** — [GitHub](https://github.com/ShashankSingh2020)

If you found this project useful, consider giving it a ⭐.
