# System Architecture & Design Specification

**Project:** FinDoc-Eval (Financial Document RAG Pipeline)

---

## 1. System Overview

FinDoc-Eval is an asynchronous, high-concurrency Retrieval-Augmented Generation (RAG) pipeline optimized for extracting, indexing, and querying multi-column financial tables and text from born-digital SEC 10-K filings. The primary engineering focus is an automated evaluation framework to systematically benchmark retrieval accuracy and latency across multiple real-world financial documents.

---

## 2. Core Architecture

The system uses a Python/FastAPI backend connected to a PostgreSQL database, functioning through a 5-stage pipeline:

1. **Auth & Gateway Middleware:** In V1, a stub middleware validates a hardcoded API key. The schema and middleware interfaces are designed for drop-in JWT/Bearer token authentication in V2 (see Section 3 for isolation design).
2. **Ingestion Engine (`pdfplumber`):** Bypasses OCR to read native PDF text layers via X-Y coordinate geometry. Specifically targeted to preserve structural integrity of tabular data (e.g., *Consolidated Statements of Income*).
3. **Vectorization Engine:** Handles chunking and asynchronous batching to the OpenAI Embeddings API (`text-embedding-3-small`, 1536 dimensions).
4. **Retrieval Engine (`pgvector`):** Executes high-speed cosine similarity (`<=>`) vector math inside the database to retrieve relevant chunks based on semantic proximity to the user's query.
5. **Synthesis Engine:** Compiles retrieved context into a strict prompt and streams the generated response from `gpt-4o` via Server-Sent Events (SSE).

---

## 3. Data Model (PostgreSQL + pgvector)

To avoid fragmented data, both relational metadata and high-dimensional vectors reside in the same PostgreSQL database.

**Table: `document_chunks`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, Primary Key | |
| `document_id` | UUID, Foreign Key | References `documents` table |
| `user_id` | String, Indexed | Present in schema for future row-level security (RLS). In V1, all rows use a single stub `user_id = "default"`. |
| `chunk_text` | Text | The actual parsed string |
| `embedding` | Vector(1536) | Dense representation from `text-embedding-3-small` |
| `metadata` | JSONB | Stores `page_number`, `source_table_name`, `token_count`, `company`, `fiscal_year` |

**Multi-Tenancy Design Note:** `user_id` is indexed and included in all queries even in V1. When JWT auth is added in V2, the only changes required are: (1) swap the stub middleware for real token validation, and (2) enable PostgreSQL Row-Level Security policies on this column. No application query logic needs to change.

---

## 4. Chunking & Ingestion Heuristics

Naive chunking destroys financial data. The pipeline implements a semantic splitting strategy:

- **Target Size:** ~512 tokens per chunk.
- **Overlap:** ~50 tokens to prevent context from being cut at sentence boundaries.
- **Table Preservation:** The parsing script detects grid layouts and converts them into Markdown format *before* chunking, ensuring columns and rows stay mathematically bound together.
- **Metadata Tagging:** Each chunk is tagged with its source company and fiscal year at ingestion time, enabling filtered retrieval across the multi-document corpus.

---

## 5. Source Documents

The V1 eval corpus consists of two SEC 10-K filings selected for their well-structured native PDF text layers:

| Company | Fiscal Year | SEC Filing |
|---|---|---|
| NVIDIA | FY2024 (Jan 2024) | 10-K |
| Apple | FY2024 (Sep 2024) | 10-K |

Using two companies ensures the retrieval pipeline is evaluated across documents with meaningfully different financial structures, reducing the risk of overfitting chunking heuristics to a single filing. Microsoft 10-K (FY2024) is planned as a post-V1 addition.

---

## 6. API Interface

All endpoints are asynchronous (`async def`) to prevent server blocking during high-latency LLM API calls.

- `POST /api/v1/documents/upload` — Accepts `multipart/form-data` PDF, returns document metadata.
- `POST /api/v1/query` — Accepts `{ "query": string, "document_id": string }`. Returns an asynchronous text stream of the answer, appended with a `source_nodes` array (the exact database chunks used).

---

## 7. Evaluation Framework

A standalone offline script (`eval/eval_harness.py`) loads `eval/golden_dataset.json`, a curated set of ~20 financial questions with ground-truth answers drawn from the V1 corpus.

The harness calculates and writes to `BENCHMARKS.md`:

- **Retrieval Accuracy:** Did the top-3 retrieved chunks contain the exact numbers needed to answer the question?
- **Answer Quality:** Does the synthesized answer match the ground-truth value?
- **Latency:** End-to-end execution time per query (ms).

Results are logged with a timestamp and a short description of what changed (e.g., "increased chunk overlap to 75 tokens") so that iteration history is preserved.

---

## 8. Project Structure

```
findoc-eval/
├── api/
│   ├── main.py              # FastAPI app, route definitions
│   └── middleware.py        # Stub auth (V1) — swap for JWT in V2
├── ingestion/
│   ├── parser.py            # pdfplumber extraction + table-to-Markdown
│   └── chunker.py           # Semantic chunking logic
├── retrieval/
│   └── vector_store.py      # pgvector query logic (cosine similarity)
├── synthesis/
│   └── engine.py            # Prompt assembly + gpt-4o streaming
├── eval/
│   ├── eval_harness.py      # Offline benchmark runner
│   └── golden_dataset.json  # 20 curated Q&A pairs
├── db/
│   └── schema.sql           # Table definitions + pgvector extension
├── tests/
├── DESIGN.md
├── BENCHMARKS.md            # Auto-updated by eval_harness.py
└── README.md
```

---

## 9. Error Handling & Fallbacks

- **Unreadable PDFs:** If a user uploads a scanned PDF without a text layer, the ingestion engine immediately aborts and returns `415 Unsupported Media Type` rather than passing empty data to the embedding API.
- **API Timeouts:** OpenAI APIs occasionally hang. The Synthesis Engine implements a strict 15-second timeout with an automatic retry.
- **Hallucination Prevention:** The LLM system prompt contains a strict fallback directive: *"If the answer cannot be explicitly found in the provided context snippets, output exactly: 'Insufficient data in source document.' Do not attempt to guess."*

---

## 10. Future Infrastructure & Scaling (Post-V1 Roadmap)

The following are strictly out of scope for V1 but planned for summer polish:

- **Full Auth (V2):** Replace stub middleware with real JWT validation. Enable PostgreSQL Row-Level Security on `user_id`. The schema is already designed for this with zero migration required.
- **Telemetry UI:** A Next.js/TypeScript dashboard to visualize `BENCHMARKS.md` metrics — retrieval accuracy over time, latency per query, and API cost tracking.
- **Cost-Control Layer:** A Redis-backed token bucket system deployed as FastAPI middleware, tracking LLM token consumption per user and tripping a circuit breaker at a configurable monthly budget limit.
- **Microsoft 10-K:** Expand the eval corpus to three companies for broader benchmark coverage.