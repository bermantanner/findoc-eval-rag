# REVIEW-PLAN.md

## Review Day Feedback

### Dax
- Suggested using XBRL files instead of PDFs for structured financial data, since SEC filings are available in machine-readable XBRL format on EDGAR
- Suggested using the SEC EDGAR API for evaluation purposes to verify ground-truth answers against an authoritative source
- Noted that a frontend to display retrieved tables cleanly would improve usability

### Michael
- Flagged that the eval harness should be the top priority before final submission — benchmarking is central to the project's purpose
- Identified that `retrieval/vector_store.py` hardcodes `user_id = "default"`, which undermines the multi-tenancy isolation the schema was designed to support
- Suggested a shared document pool: since all 10-K filings are public data, users should not need to re-upload a document another user has already ingested

### Magnus
- Identified that `search_chunks` always returns the top-5 chunks regardless of similarity score, meaning unrelated chunks can be passed to the LLM and cause hallucination
- Suggested adding a similarity/confidence gate that filters out chunks below a minimum threshold before synthesis

---

## Planned Responses

### Implement for final submission
- **Eval harness** (`eval/eval_harness.py`, `eval/golden_dataset.json`, `BENCHMARKS.md`) — core deliverable, highest priority
- **Similarity confidence gate** in `retrieval/vector_store.py` — add a minimum similarity threshold; if no chunks qualify, return "Insufficient data" without calling the LLM. Directly addresses Magnus's hallucination concern and improves the accuracy results the eval harness will measure
- **Fix `user_id` hardcoding** in `retrieval/vector_store.py` — pass `user_id` as a parameter rather than hardcoding `"default"`, keeping the multi-tenancy design intact

### Noted as roadmap items (post-final)
- **XBRL integration** — XBRL captures structured numbers well but misses the 80% of a 10-K that is narrative text. A hybrid approach (XBRL for numeric precision + PDF pipeline for prose) would strengthen the system and is planned for summer
- **SEC EDGAR API for eval** — using EDGAR to verify ground-truth answers rather than hand-curating them would improve eval credibility; planned as an enhancement to the harness
- **Shared document pool** — since all ingested documents are public SEC filings, a shared pool would eliminate redundant uploads and expand the retrievable corpus for all users; planned for V2
- **Frontend** — a minimal Next.js dashboard for visualizing retrieved tables and benchmark metrics is planned for summer
