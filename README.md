# FinDoc-Eval: Financial Document RAG Pipeline

An asynchronous RAG (Retrieval-Augmented Generation) pipeline for querying SEC 10-K financial filings. Upload a PDF, ask a question, get an answer grounded in the exact source passages — returned with the page number and similarity score of every chunk used.

The primary engineering focus is the **evaluation harness**. Against 10 curated questions from the NVIDIA FY2025 10-K, the system scores **60% answer correctness**, identical across three consecutive passes. One open-ended question has flipped between passing and failing across a wider sample, so the honest spread is closer to ±5pp — three passes is a small sample for estimating variance, and ±0pp is not a determinism claim.

The error bar is the point. An earlier version of this benchmark reported a single number — 70% — that turned out not to be reproducible: re-running it two months later against the same document with no code changes produced 60%. Neither the synthesis call nor the LLM judge was pinned to `temperature=0`, so every run resampled both the answer *and* its grade. See [Reproducibility](#reproducibility) and [Known Limitations](#known-limitations).

---

## What it does

1. **Ingest** — Upload a native-text-layer PDF. The pipeline extracts text and tables (tables are converted to Markdown to preserve row/column structure), chunks the content into ~512-token segments with ~50-token overlap, generates embeddings via OpenAI, and stores them in PostgreSQL + pgvector.
2. **Retrieve** — The query is embedded and matched against the vector store by cosine similarity. A **confidence gate** rejects results below a minimum similarity; if nothing clears it, the pipeline returns "Insufficient data" without calling the LLM at all.
3. **Synthesize** — Retrieved chunks are assembled into a strict prompt and answered by `gpt-4o` at `temperature=0`, constrained to the provided context. Every response carries its sources.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | Python, FastAPI (async) |
| Database | PostgreSQL + pgvector (HNSW index) |
| PDF Parsing | pdfplumber |
| Embeddings | OpenAI `text-embedding-3-small` (1536 dims) |
| Synthesis | OpenAI `gpt-4o` (`temperature=0`) |
| Eval Judge | OpenAI `gpt-4o-mini` (LLM-as-judge, `temperature=0`) |
| Tokenization | tiktoken (`cl100k_base`) |
| Infrastructure | Docker, Docker Compose |

---

## API

All endpoints require an `X-API-Key: dev-secret-key` header except `/health`.

### `GET /health`
Returns `{"status": "ok"}` if the API and database are reachable.

### `POST /api/v1/documents/upload`
Upload a PDF for ingestion.

**Form fields:** `file` (PDF), `company` (string), `fiscal_year` (string)

```json
{"document_id": "<uuid>", "chunks_stored": 340}
```

### `POST /api/v1/query`
Query an ingested document. Returns structured JSON by default.

**Body:**
```json
{"query": "What was NVIDIA's total revenue for fiscal year 2025?", "document_id": "<uuid>"}
```

**Response:**
```json
{
  "query": "What was NVIDIA's total revenue for fiscal year 2025?",
  "document_id": "<uuid>",
  "answer": "NVIDIA's total revenue for fiscal year 2025 was $130,497 million.",
  "chunks": [
    {
      "text": "...",
      "similarity": 0.686,
      "page": 52,
      "company": "NVIDIA",
      "fiscal_year": "FY2025",
      "block_type": "table"
    }
  ]
}
```

If no chunk clears the similarity gate, the endpoint returns **200** with `"answer": "Insufficient data in source document."` and an empty `chunks` array — a refusal is a system behavior, not a transport error, and the eval harness needs to tell those apart.

Add `?stream=true` to receive Server-Sent Events instead: `token` events, then a `source_nodes` event, then `[DONE]`.

Interactive schema documentation is served at `/docs`.

---

## Eval Harness

```bash
python3 eval/eval_harness.py --document-id <uuid> [--runs 3]
```

Loads `eval/golden_dataset.json` (10 curated Q&A pairs from the NVIDIA FY2025 10-K), queries the live API for each, and grades the results. Output is written to `BENCHMARKS.md`.

Two dimensions are measured:

- **Answer correctness** — graded by `gpt-4o-mini` against a financial-domain rubric that allows rounding and paraphrase, but rejects vague answers and rejects "Insufficient data" when an answer exists.
- **Retrieval confidence** — cosine similarity of the top returned chunk against a 0.60 threshold. **This is a proxy, not a retrieval-correctness metric** — see Known Limitations.

With `--runs > 1`, the harness repeats the full pass and reports the mean, the range, and which questions were unstable across runs.

Requires `httpx`, `openai`, and `python-dotenv` installed locally (the harness runs on the host, against the containerized API).

---

## Reproducibility

LLM output is sampled, so an evaluation harness is only useful if its own variance is smaller than the effects it is trying to measure. Steps taken:

- `temperature=0` is pinned on the synthesis call, the streaming call, and the judge call.
- Synthesis parameters are built in one place (`_completion_kwargs`) so the streaming and non-streaming paths cannot silently diverge.
- The judge was verified deterministic under fixed input: eight identical verdicts in eight runs on the same answer. Residual variance in the benchmark comes from **synthesis**, not from grading.
- `temperature=0` is not an absolute guarantee — floating-point non-associativity and request batching still permit rare divergence on near-tied tokens — so results are reported as a mean and range over repeated runs rather than a single figure.

---

## Known Limitations

These are measured, not hypothetical.

**"Retrieval hit rate" does not measure retrieval.** It reports the cosine similarity of the top-ranked chunk against a fixed threshold. Cosine magnitude correlates strongly with chunk length and density, so the metric partly measures how chunky a passage is rather than whether it is the right one — and it inspects only rank 1 of the 5 chunks actually passed to the model. Two benchmark questions score as retrieval "hits" while the system answers "Insufficient data." *Fix in progress: record ground-truth source pages per question and compute recall@k and MRR.*

**Embeddings discriminate poorly within a topic.** They separate "revenue" from "board meetings" easily, but separate "Data Center segment revenue" from "total revenue" barely at all. This is the direct cause of two benchmark failures. *Fix: hybrid retrieval — vector search for recall, keyword or re-ranking for precision.*

**Retrieval is sensitive to query phrasing.** `"What was NVIDIA's total revenue for fiscal year 2025?"` retrieves at 0.686; `"What was total revenue?"` — the same question — retrieves at 0.429 and is rejected by the confidence gate. The gate threshold is calibrated against a golden dataset whose questions are all written in the same formal register, so the benchmark cannot currently see this failure.

**The judge is unvalidated against human labels.** It is deterministic, but nobody has confirmed its grades match a human's. *Fix: hand-label the set once and measure judge/human agreement.*

**The golden answers have not been verified against the source PDF.** Several were taken from public sources. The eval already caught one consequence: NVIDIA does not report "Data Center" and "Gaming" as financial segments — its reporting segments are Compute & Networking and Graphics — so two expected answers describe a breakdown that appears only in a footnote.

**Scale is one document.** 340 chunks, one filing. The similarity threshold and retrieval behavior would not transfer unchanged to a multi-company corpus without metadata pre-filtering.

---

## Project Structure

```
findoc-eval-rag/
├── api/
│   ├── main.py              # FastAPI app, Pydantic response models, routes
│   └── middleware.py        # Stub API key auth (V2: JWT + RLS)
├── ingestion/
│   ├── parser.py            # pdfplumber extraction, table-to-Markdown
│   ├── chunker.py           # tiktoken chunking, header-preserving table splits
│   └── vectorizer.py        # Async OpenAI embeddings
├── retrieval/
│   └── vector_store.py      # pgvector writes, cosine search, similarity gate
├── synthesis/
│   └── engine.py            # Prompt assembly, gpt-4o synthesis and SSE streaming
├── eval/
│   ├── eval_harness.py      # Benchmark runner (LLM-as-judge, multi-run)
│   └── golden_dataset.json  # 10 curated Q&A pairs from NVIDIA FY2025 10-K
├── db/
│   └── schema.sql           # Table definitions, pgvector extension, HNSW index
├── ask.py                   # Interactive CLI client
├── DESIGN.md                # System architecture specification
├── DEMO.md                  # Setup and usage instructions
├── BENCHMARKS.md            # Auto-generated benchmark results
└── REGRETS.md               # Post-mortem and lessons learned
```

---

## Roadmap

- Ground-truth source pages → recall@k and MRR
- Hybrid retrieval (vector + keyword) for fine-grained financial distinctions
- Section-aware chunking on 10-K Item boundaries
- Expanded golden dataset, including colloquial phrasings and per-tag reporting
- Apple and Microsoft 10-Ks as additional eval corpora
- JWT auth + PostgreSQL row-level security on `user_id`

---

## Setup

See [DEMO.md](DEMO.md) for full build and usage instructions.
