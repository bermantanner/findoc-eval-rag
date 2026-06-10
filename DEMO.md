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

The easiest way to query is the interactive CLI. Pass the `document_id` from step 5:

```bash
python3 ask.py <your-document-id>
```

You'll be prompted for questions in a loop:

```
Ask a question (or 'quit' to exit): What was total revenue in FY2025?

============================================================
ANSWER
============================================================
NVIDIA's total revenue in FY2025 was $130,497 million.

============================================================
SOURCES
============================================================
[1] NVIDIA FY2025 — Page 52 (similarity: 0.65)
    ...Consolidated Statements of Income...Revenue $ 130,497 $ 60,922 $ 26,974...

...
```

Type `quit` to exit.

### Raw API (optional)

For direct API access the endpoint accepts JSON and returns plain text with `?format=plain`:

```bash
curl -X POST "http://localhost:8000/api/v1/query?format=plain" \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "What was total revenue in FY2025?", "document_id": "<your-document-id>"}'
```

Omit `?format=plain` to receive a raw Server-Sent Events stream instead.

---

---

## 7. Run the eval harness (optional)

The eval harness benchmarks the system against 10 curated questions from the NVIDIA FY2025 10-K. It runs locally and hits the API over HTTP, so the stack must be running.

Install the harness dependencies locally:

```bash
pip install httpx openai python-dotenv
```

Run the benchmark, passing the `document_id` from step 5:

```bash
python3 eval/eval_harness.py --document-id <your-document-id>
```

Results are printed to the terminal in real time and written to `BENCHMARKS.md` when complete.

---

## Notes

- The API key for V1 is hardcoded as `dev-secret-key`. Full JWT authentication is planned for V2.
- Only native-text-layer PDFs are supported. Scanned PDFs (image-only) will return `415 Unsupported Media Type`.
- The similarity confidence gate (`min_similarity=0.5`) will return a 404 if no retrieved chunks are relevant enough. This is intentional — it prevents the LLM from being called on unrelated queries.
- To stop the stack: `docker compose down`. To also delete the database volume: `docker compose down -v`.
