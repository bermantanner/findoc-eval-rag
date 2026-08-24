# DEMO — Building and Running FinDoc-Eval

These instructions build the full stack from scratch using Docker. Tested on macOS and Linux.

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

This will parse, chunk, embed (340 chunks for the NVIDIA FY2025 10-K), and store everything in the database. The process takes 30–60 seconds depending on document size.

Expected response:
```json
{"document_id": "daf8d328-94e5-4024-aeef-db57e94ed2f2", "chunks_stored": 340}
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

The endpoint accepts JSON and returns structured JSON:

```bash
curl -s -X POST "http://localhost:8000/api/v1/query" \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "What was NVIDIA total revenue for fiscal year 2025?", "document_id": "<your-document-id>"}' \
  | python3 -m json.tool
```

```json
{
  "query": "What was NVIDIA total revenue for fiscal year 2025?",
  "document_id": "<your-document-id>",
  "answer": "NVIDIA's total revenue for fiscal year 2025 was $130,497 million.",
  "chunks": [
    {"text": "...", "similarity": 0.686, "page": 52,
     "company": "NVIDIA", "fiscal_year": "FY2025", "block_type": "table"}
  ]
}
```

Add `?stream=true` to receive Server-Sent Events instead (`-N` disables curl buffering so you see tokens arrive individually):

```bash
curl -N -X POST "http://localhost:8000/api/v1/query?stream=true" \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "What was NVIDIA total revenue for fiscal year 2025?", "document_id": "<your-document-id>"}'
```

Interactive schema docs are served at **http://localhost:8000/docs**.

> **Note on phrasing:** retrieval is sensitive to how a question is worded. `"What was NVIDIA's total revenue for fiscal year 2025?"` retrieves at similarity 0.686, while `"What was total revenue?"` — the same question — retrieves at 0.429 and is rejected by the confidence gate. Use specific phrasing when testing.

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

Add `--runs 3` to repeat the full pass and report a mean and spread instead of a single
score. This matters: LLM output is sampled, so a single run cannot distinguish a real
change from a re-roll.

```bash
python3 eval/eval_harness.py --document-id <your-document-id> --runs 3
```

Results are printed to the terminal in real time and written to `BENCHMARKS.md` when
complete, including which questions were unstable across passes and a per-tag breakdown.

---

## Notes

- The API key for V1 is hardcoded as `dev-secret-key`. Full JWT authentication is planned for V2.
- Only native-text-layer PDFs are supported. Scanned PDFs (image-only) will return `415 Unsupported Media Type`.
- The similarity confidence gate (`min_similarity=0.5`) returns **200** with `"answer": "Insufficient data in source document."` and an empty `chunks` array when nothing is relevant enough. The LLM is never called in that case — it saves the API cost and prevents the model from answering on unrelated context. It deliberately is *not* a 404: a refusal is a system behavior, and the eval harness needs to distinguish it from a transport failure.
- To stop the stack: `docker compose down`. To also delete the database volume: `docker compose down -v`.
