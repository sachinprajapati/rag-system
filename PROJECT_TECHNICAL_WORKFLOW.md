# Askwise RAG System: Project and Technical Workflow

## 1. Purpose

Askwise is a multi-tenant Retrieval-Augmented Generation (RAG) application for uploading documents and asking grounded questions about them. It provides a React user interface, a FastAPI service, vector and keyword retrieval, local LLM generation through Ollama, optional Keycloak authentication, conversation history, and operational monitoring.

## 2. System architecture

```text
Browser (React/Vite, :3000)
        |
        | upload, query, conversation, monitoring requests
        v
FastAPI API (:8000, /api/*) <---- Keycloak (:8080, optional OIDC/JWT)
        |
        +-- Document ingestion --> parser/router --> embeddings --> FAISS + BM25
        |
        +-- Query --> structured-data handling or retrieval --> Ollama (:11434 internal)
        |                                                   --> answer + sources
        |
        +-- Conversations and monitoring ------------------> Redis (:6379)
```

Docker Compose supplies Keycloak, Ollama, Redis, backend, and frontend. Ollama is published on host port `11435` because its container uses internal port `11434`.

## 3. Main components

| Area | Implementation | Responsibility |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite | Upload files, select retrieval method, display answers/sources, manage conversations, show monitoring. |
| API | FastAPI | Exposes `/api` routes, applies CORS and optional authentication/role dependencies. |
| Parsing and chunking | Local parsers and LangChain splitters | Routes PDF, DOCX, CSV, code, Markdown/HTML/XML, and plain text to appropriate extraction and chunking strategies. |
| Embeddings and vector search | `all-MiniLM-L6-v2` and FAISS | Creates 384-dimensional embeddings and persists the FAISS index plus chunk metadata. |
| Keyword search | BM25 | Rebuilds after ingestion/deletion and supports tenant-filtered lexical search. |
| Generation | Ollama, default `llama3.2:1b` | Answers only from retrieved context; returns a formatted context fallback if Ollama is unavailable. |
| Authentication | Keycloak + JWT validation | Optional OIDC authentication, roles, and tenant claims. |
| State and observability | Redis | Stores conversations/chat history and monitoring records in separate logical databases. |

## 4. Document ingestion workflow

1. An administrator uploads a file through `POST /api/documents/upload`.
2. The API retains the original filename and extension, writes a temporary file, and performs parsing/indexing in a worker thread so it does not block the async request loop.
3. The document router classifies the file:
   - PDF: extracts text with `pdfplumber` when available, falls back to `pypdf`, detects tables, and creates recursive text chunks plus parent/child table chunks.
   - DOCX: reads Word XML and recursively chunks text.
   - CSV: creates one self-contained chunk per row, retaining a normalized `row_data` map for exact lookups and aggregates.
   - Code: applies language-aware structural splitting.
   - Markdown, HTML, and XML: splits along structural headers/elements.
   - Other text: applies recursive character chunking.
4. Each chunk receives metadata such as source filename, chunk index, hash, size estimates, strategy, upload time, uploader, and `tenant_id`.
5. The backend generates embeddings, adds embeddings and metadata to FAISS, persists the index, and rebuilds the BM25 index.
6. The temporary upload is removed after processing. The response reports file type, strategy, chunk count, and tenant.

The prose/PDF chunking implementation uses 700-character chunks with 140-character overlap. Structural/code splitting uses larger language-aware boundaries; CSV preserves complete rows instead of treating them as prose.

## 5. Query and answer workflow

1. The user submits `POST /api/query` with `query`, optional `top_k` (default `5`), `search_method` (`hybrid`, `vector`, or `keyword`), and an optional `conversation_id`.
2. When authentication is active, the request must resolve to a user with a tenant claim. Retrieval is scoped to that tenant.
3. For CSV-like records, the backend first detects exact field/value lookups and count, average, sum, min, max, missing-value, comparison, and grouping queries. These calculations inspect all matching tenant rows, not only the normal `top_k` window, and may return a table.
4. For ordinary retrieval:
   - **Vector**: embeds the question and searches FAISS by L2 distance.
   - **Keyword**: searches BM25.
   - **Hybrid**: retrieves candidates from both, uses normalized weighted fusion (vector `0.7`, keyword `0.3`) by default, then cross-encoder reranks up to 20 fused candidates before returning `top_k`; reciprocal-rank fusion is also implemented. If the local reranker model is unavailable, it safely returns the fused ranking.
5. The generator builds a prompt from up to five retrieved chunks and calls Ollama with a grounding instruction. Exact structured lookups can be answered directly from row metadata.
6. The API returns the answer, retrieved chunks, source filenames, optional table, tenant (when authenticated), and conversation ID.
7. The exchange is saved to Redis conversation history. Query timings, errors, and grounding-related monitoring data are logged independently.

## 6. Authentication, authorization, and tenant isolation

Authentication is configured but disabled by default (`AUTH_ENABLED=false`). Enable it with `AUTH_ENABLED=true` in the backend environment and configure Keycloak realm `rag-system`, backend client `rag-backend`, and frontend client `rag-frontend`.

Roles:

| Role | Access |
| --- | --- |
| `admin` | Upload and delete documents; all normal authenticated functions. |
| `user` | Query, conversations, and chat history. |
| `viewer` | Read document listings; role checks also permit higher roles where applicable. |

The `tenant_id` claim is applied to document metadata during ingestion. Document listings, deletions, vector results, BM25 results, structured-record operations, and chat/conversation operations use that tenant scope. A filename deletion is constrained to the caller's tenant and does not reveal same-named files in other tenants.

For production, use HTTPS, a non-default Keycloak administrator password, correctly configured redirect URIs/CORS origins, secure client settings, a robust JWKS key-selection strategy, and persistent/managed storage appropriate for the deployment.

## 7. Conversation and monitoring workflow

### Conversations

Queries create or continue a conversation. The API also supports creating, listing, retrieving, renaming, and deleting conversations, plus reading or clearing a user's history. Redis keys and service methods scope records by both user and tenant, preventing one user from accessing another user's conversation.

### Monitoring

Every query records latency, retrieval details, result count, search mode, sources, conversation ID, errors, and a heuristic hallucination/grounding score. The monitoring service uses Redis database 2; latency events have seven-day retention and rolling latency statistics use a 30-day retention.

The dashboard and API expose system metrics, query logs, error statistics, flagged hallucinations, latency statistics, and a monitoring health view.

## 8. API reference

Interactive API documentation is available at `http://localhost:8000/docs`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | API metadata and docs link. |
| GET | `/api/health/health` | Basic service health. |
| POST | `/api/documents/upload` | Upload and ingest a document (admin when auth is enabled). |
| GET | `/api/documents/list` | List documents in the current tenant. |
| DELETE | `/api/documents/{file_name}` | Delete all matching indexed chunks in the current tenant (admin). |
| POST | `/api/query` | Run RAG or structured-data query. |
| GET/DELETE | `/api/query/history` | Get or clear current user's chat history. |
| POST/GET | `/api/query/conversations` | Create or list conversations. |
| GET/PUT/DELETE | `/api/query/conversations/{conversation_id}` | Get, rename, or delete a conversation. |
| GET | `/api/auth/status`, `/api/auth/me`, `/api/auth/admin-only` | Auth status, identity, and role-check endpoint. |
| POST | `/api/auth/logout` | Logout acknowledgement. |
| GET | `/api/monitoring/metrics`, `/queries`, `/errors`, `/hallucinations`, `/latency/{operation}`, `/health` | Observability data and health. |

## 9. Local setup and operation

Prerequisites: Docker and Docker Compose. Python and Node.js are needed only when running services outside containers.

```bash
docker compose up --build
```

Open the frontend at `http://localhost:3000`, backend docs at `http://localhost:8000/docs`, and Keycloak administration at `http://localhost:8080`.

Use `./start-all.sh` for the existing helper-based startup flow and `./stop-all.sh` to stop it. The backend can also be run from `backend` with its declared Python dependencies; the frontend can be run from `frontend` with `npm install` then `npm run dev`.

Important environment values:

| Setting | Default | Purpose |
| --- | --- | --- |
| `REDIS_URL` | `redis://localhost:6379/0` | Main Redis connection. |
| `FAISS_INDEX_PATH` | `./faiss_index` | Persisted FAISS index and metadata location. |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model. |
| `RERANKER_ENABLED`, `RERANKER_MODEL`, `RERANKER_CANDIDATE_COUNT` | `true`, `cross-encoder/ms-marco-MiniLM-L6-v2`, `20` | Enables/configures local cross-encoder reranking of hybrid candidates. |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama address; Compose backend uses the internal container URL. |
| `OLLAMA_MODEL` | `llama3.2:1b` | Generation model. |
| `AUTH_ENABLED` | `false` | Enables Keycloak JWT and role enforcement. |
| `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID` | localhost / `rag-system` / `rag-backend` | Backend OIDC configuration. |
| `VITE_API_URL` | `http://localhost:8000/api` | Frontend API base URL; it must include `/api`. |

## 10. Validation and troubleshooting

Run the backend checks from `backend`:

```bash
pytest
python verify_setup.py
```

Useful checks:

```bash
docker compose ps
curl http://localhost:8000/api/health/health
curl http://localhost:8080/realms/rag-system/.well-known/openid-configuration
```

If Keycloak fails to initialize, first confirm that its container is running and port 8080 is available. If requests return `401` or `403`, verify `AUTH_ENABLED`, bearer-token forwarding, roles, and the `tenant_id` claim. If generation fails, confirm the selected Ollama model is available; retrieval will still return a context-based fallback answer. If the frontend cannot reach the API, ensure its API base URL includes `/api` and that the configured origin is allowed by backend CORS.

## 11. Repository map

```text
backend/src/api/routes/       HTTP endpoints
backend/src/core/             configuration, authentication, tenant utilities
backend/src/services/         ingestion, retrieval, generation, monitoring, history
backend/src/db/               FAISS and Redis adapters
backend/src/utils/            parsers, file router, splitters, retries
backend/tests/                backend tests
frontend/src/components/      upload, query, results, conversations, monitoring UI
frontend/src/services/api.ts  frontend HTTP client
docker-compose.yml            local multi-service deployment
```

This file is the project documentation source of truth. Keep it updated when an architectural, API, configuration, or operational workflow changes.
