# findoc-eval-rag
## Title:

FinDoc-Eval: Automated Benchmarking for Financial Document Retrieval

## One sentence description:

Intelligent search engine to query complex SEC financial filings, using custom automated Python test suite to measure and improve data retrieval accuracy (Ship with auth + live URL)

---

## Planned technologies:

> For the backend I plan to use Python with FastAPI for handling the concurrent API requests and streaming text responses.

**(a) Implemented as written.** FastAPI is the backend framework with fully async endpoints and Server-Sent Events streaming. See `api/main.py`.

> For the database, I want to use PostgreSQL and an extension so I can store the app data and vector embeddings in the same place.

**(a) Implemented as written.** PostgreSQL with the `pgvector` extension is running in Docker. The `documents` and `document_chunks` tables store both relational metadata and 1536-dimension embedding vectors in the same database. See `db/schema.sql` and `docker-compose.yml`.

> For the LLM layer I probably will use Anthropic.

**(a) Implemented — with a change.** The LLM layer is implemented using OpenAI instead of Anthropic: `text-embedding-3-small` for embeddings and `gpt-4o` for synthesis. See `ingestion/vectorizer.py` and `synthesis/engine.py`.

> For deployment, I'll do Docker containers hosted on AWS or Vercel using a simple auth setup to keep user data separate.

**(b) Partially implemented.** Docker is fully implemented — the entire stack runs with `docker compose up`. Cloud deployment to AWS/Vercel did not ship for the final submission; the system runs locally. A stub auth middleware is in place (`api/middleware.py`) using a hardcoded API key; full JWT-based user auth with row-level security is planned for V2 (summer roadmap).

---

## First deliverable:

> I want to have a working backend API endpoint where an authenticated user can upload a single SEC 10-K financial PDF.

**(a) Implemented as written.** `POST /api/v1/documents/upload` requires a valid `X-API-Key` header. See `api/main.py` and `api/middleware.py`.

> System will extract the text, split it into chunks, generate embeddings, and save everything into the vector database.

**(a) Implemented as written.** The full ingestion pipeline is:
- Text + table extraction: `ingestion/parser.py` (pdfplumber, tables converted to Markdown)
- Chunking: `ingestion/chunker.py` (~512 tokens, ~50 token overlap, table rows kept intact)
- Embedding: `ingestion/vectorizer.py` (OpenAI `text-embedding-3-small`, async batched)
- Storage: `retrieval/vector_store.py` (pgvector, cosine similarity index)

> The user can then send a text question and get back the exact paragraphs needed to answer it.

**(a) Implemented as written.** `POST /api/v1/query` embeds the query, retrieves the top-5 most similar chunks via cosine similarity, synthesizes a streamed answer via `gpt-4o`, and returns the exact source chunks used. See `api/main.py`, `retrieval/vector_store.py`, and `synthesis/engine.py`.

---

## Rough architecture for the first deliverable:

> 1. Auth Middleware (intercept incoming request to verify user tokens)

**(a) Implemented as written.** `api/middleware.py` — stub validates a hardcoded API key on all protected routes. Schema is designed for drop-in JWT replacement in V2 with no query logic changes required.

> 2. Ingestion & Parser pipeline (takes raw PDF, uses python libraries to pull out text while preserving layout of the financial tables)

**(a) Implemented as written.** `ingestion/parser.py` — uses `pdfplumber` to read native PDF text layers. Detects table grid layouts and converts them to Markdown before chunking to preserve row/column structure. Aborts with an error on scanned PDFs with no text layer.

> 3. Vectorization Engine (slices the processed text into chunks, passes them to embedding API, and gets back data vectors)

**(a) Implemented as written.** Split across two files: `ingestion/chunker.py` handles the slicing (~512 tokens via `tiktoken`, ~50 token overlap, table-aware splitting), and `ingestion/vectorizer.py` handles async batched calls to the OpenAI embeddings API.

> 4. Retrieval Engine (takes user question, turns it into a vector, runs a similarity query against pgvector, and returns most relevant matching text snippets)

**(a) Implemented as written.** `retrieval/vector_store.py` — embeds the query, executes a cosine similarity search (`<=>` operator) against the `document_chunks` table, and returns the top-k results with similarity scores and metadata.

> 5. Synthesis Engine (packages the retrieved financial snippets alongside user's question into a clean prompt, hits LLM, streams final answer back)

**(a) Implemented as written.** `synthesis/engine.py` — assembles retrieved chunks into a strict prompt with a hallucination-prevention directive, streams the `gpt-4o` response as SSE tokens, and appends a final `source_nodes` event with the exact chunks used.

---

## After first deliverable goals:

> The Testing Harness: I will write standalone python script with a fixed gold dataset of many complex numeric questions directly mapped to the real financial answers in the filings.

**(a) Implemented.** `eval/eval_harness.py` — standalone script that loads `eval/golden_dataset.json` (10 curated Q&A pairs verified against the NVIDIA FY2025 10-K), hits the live API, and scores each result on two dimensions: retrieval confidence (top chunk cosine similarity vs. a 0.60 threshold) and answer correctness (graded by a `gpt-4o-mini` LLM judge). Results are written to `BENCHMARKS.md` with timestamps, per-question judge reasoning, and a Failed Cases section for diagnosis. Final benchmark: **70% answer correctness, 90% retrieval hit rate**. The eval framework also drove a targeted fix to `ingestion/parser.py` — a table Markdown formatting bug was identified through benchmark regression and corrected, improving correctness from 60% to 70%.

> Retrieval Tuning: I'll implement and test different test splitting methods to raise test scores

**(b) Partially implemented.** A similarity confidence gate was added to `retrieval/vector_store.py` (`min_similarity=0.5` parameter): if no retrieved chunks score above the threshold, the LLM is skipped entirely and an empty result is returned, preventing hallucination on irrelevant queries and saving API cost. Full chunking parameter ablation (varying `CHUNK_SIZE`, `CHUNK_OVERLAP`, `top_k`) was not completed — this is the primary planned continuation for summer, using `BENCHMARKS.md` as the measurement baseline.

> Developer dashboard: If there's time, a clean minimal TypeScript/Next.js dashboard that tracks the system metrics. (Im thinking like look-up speed, API costs, current accuracy?)

**(b) Planned.** Planned as a Next.js/TypeScript frontend that visualizes `BENCHMARKS.md` metrics — retrieval accuracy over time, latency per query, and API cost tracking. Lower priority than the eval harness.

> Cost guardrails: If there's time, a simple Redis tool to log API usage per user, which blocks further queries if an account hits a safe monthly budget ceiling.

**(b) Planned.** Will be implemented as a Redis-backed token bucket deployed as FastAPI middleware, tracking LLM token consumption per user. Planned for the final submission if time permits.
