# DEMO — Building and Running FinDoc-Eval

These instructions build the full stack from scratch on a Linux environment using Docker.

---

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/) and Docker Compose (included with Docker Desktop)
- An [OpenAI API key](https://platform.openai.com/api-keys)
- A native-text-layer PDF (e.g. a SEC 10-K filing downloaded directly from [EDGAR](https://www.sec.gov/cgi-bin/browse-edgar))

---

## 1. Clone the repository

```bash
git clone <repo-url>
cd findoc-eval-rag
```

---

## 2. Configure environment variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and set your OpenAI API key:

```
OPENAI_API_KEY=your-openai-api-key-here
DATABASE_URL=postgresql://findoc:findoc@db:5432/findoc
```

---

## 3. Start the stack

```bash
docker compose up --build
```

This will:
- Pull and start a PostgreSQL 16 + pgvector container
- Run `db/schema.sql` on first startup (creates tables and vector index)
- Build and start the FastAPI API container on port `8000`

Wait until you see the API container log:
```
INFO:     Application startup complete.
```

---

## 4. Verify the API is running

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok"}
```

---

## 5. Upload a document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "X-API-Key: dev-secret-key" \
  -F "file=@/path/to/your/10k.pdf" \
  -F "company=NVIDIA" \
  -F "fiscal_year=FY2025"
```

This will parse, chunk, embed (344 chunks for the NVIDIA FY2025 10-K), and store everything in the database. The process takes 30–60 seconds depending on document size.

Expected response:
```json
{"document_id": "daf8d328-94e5-4024-aeef-db57e94ed2f2", "chunks_stored": 344}
```

Save the `document_id` — you'll need it to query.

---

## 6. Query the document

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "What was total revenue in FY2025?", "document_id": "<your-document-id>"}'
```

The response streams as Server-Sent Events:

```
data: {"type": "token", "content": "NVIDIA"}
data: {"type": "token", "content": "'s total revenue"}
...
data: {"type": "source_nodes", "chunks": [...]}
data: [DONE]
```

Each `token` event contains a piece of the generated answer. The final `source_nodes` event contains the exact database chunks used to produce the answer, including page numbers and similarity scores.

---

## Notes

- The API key for V1 is hardcoded as `dev-secret-key`. Full JWT authentication is planned for V2.
- Only native-text-layer PDFs are supported. Scanned PDFs (image-only) will return `415 Unsupported Media Type`.
- To stop the stack: `docker compose down`. To also delete the database volume: `docker compose down -v`.
