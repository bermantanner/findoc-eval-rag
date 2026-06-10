# FinDoc-Eval: Financial Document RAG Pipeline

An asynchronous RAG (Retrieval-Augmented Generation) pipeline for querying SEC 10-K financial filings. Upload a PDF, ask a question, get a streamed answer grounded in the exact source passages — with the retrieved chunks returned alongside the response.

The primary engineering focus is an automated evaluation framework that benchmarks retrieval accuracy and answer correctness using an LLM-as-judge approach. Tested against 10 curated questions from the NVIDIA FY2025 10-K: **70% answer correctness, 90% retrieval hit rate**.

---

## What it does

1. **Ingest** — Upload a native-text-layer PDF via the API. The pipeline extracts text and tables (tables are converted to Markdown to preserve structure), chunks the content into ~512-token segments with overlap, generates embeddings via OpenAI, and stores everything in PostgreSQL + pgvector.
2. **Retrieve** — A query is embedded and run against the vector store using cosine similarity to find the most relevant chunks.
3. **Synthesize** — Retrieved chunks are assembled into a strict prompt and streamed through `gpt-4o`, with a hallucination-prevention directive. The response streams as Server-Sent Events, with the source chunks appended at the end.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | Python, FastAPI (async) |
| Database | PostgreSQL + pgvector |
| PDF Parsing | pdfplumber |
| Embeddings | OpenAI `text-embedding-3-small` (1536 dims) |
| Synthesis | OpenAI `gpt-4o` (SSE streaming) |
| Eval Judge | OpenAI `gpt-4o-mini` (LLM-as-judge) |
| Tokenization | tiktoken (`cl100k_base`) |
| Infrastructure | Docker, Docker Compose |

---

## API

All endpoints require `X-API-Key: dev-secret-key` header except `/health`.

### `GET /health`
Returns `{"status": "ok"}` if the API and database are reachable.

### `POST /api/v1/documents/upload`
Upload a PDF for ingestion.

**Form fields:** `file` (PDF), `company` (string), `fiscal_year` (string)

**Response:**
```json
{"document_id": "<uuid>", "chunks_stored": 344}
```

### `POST /api/v1/query`
Query an ingested document.

**Body:**
```json
{"query": "What was total revenue in FY2025?", "document_id": "<uuid>"}
```

**Response:** SSE stream of `token` events, followed by a `source_nodes` event and `[DONE]`.

Add `?format=plain` to receive a formatted plain-text response instead of SSE.

---

## Eval Harness

Run the automated benchmark against a live document:

```bash
python3 eval/eval_harness.py --document-id <uuid>
```

Loads `eval/golden_dataset.json` (10 curated Q&A pairs from the NVIDIA FY2025 10-K), queries the API for each, and scores results on two dimensions:

- **Retrieval confidence** — cosine similarity of the top returned chunk vs. a 0.60 threshold
- **Answer correctness** — graded by `gpt-4o-mini` with a financial-domain judge prompt

Results are written to `BENCHMARKS.md`. Requires `httpx`, `openai`, and `python-dotenv` installed locally.

---

## Project Structure

```
findoc-eval-rag/
├── api/
│   ├── main.py              # FastAPI app and route definitions
│   └── middleware.py        # Stub API key auth (V2: JWT + RLS)
├── ingestion/
│   ├── parser.py            # pdfplumber extraction, table-to-Markdown
│   ├── chunker.py           # tiktoken-based semantic chunking
│   └── vectorizer.py        # Async OpenAI embeddings
├── retrieval/
│   └── vector_store.py      # pgvector writes and cosine similarity search
├── synthesis/
│   └── engine.py            # Prompt assembly and gpt-4o SSE streaming
├── eval/
│   ├── eval_harness.py      # Standalone benchmark runner (LLM-as-judge)
│   └── golden_dataset.json  # 10 curated Q&A pairs from NVIDIA FY2025 10-K
├── db/
│   └── schema.sql           # Table definitions and pgvector extension
├── proposal/
│   ├── original_proposal.md
│   └── marked_up_proposal.md
├── DESIGN.md                # Full system architecture specification
├── DEMO.md                  # Setup and usage instructions
├── BENCHMARKS.md            # Auto-generated benchmark results
└── REGRETS.md               # Post-mortem and lessons learned
```

---

## Setup

See [DEMO.md](DEMO.md) for full build and usage instructions.

## Demo
https://youtu.be/G7z_XG-T8DY

