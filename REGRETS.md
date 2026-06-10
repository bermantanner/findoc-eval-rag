# REGRETS.md

## What I'd Do Differently

**Pacing.** The eval harness was always the most interesting part of this project, and I left it for last. If I had built it earlier, I could have used it to guide decisions throughout — like catching the table formatting issue in the parser weeks ago instead of the night of submission. I'd rather have shipped a rougher pipeline and spent more time iterating on the benchmark.

**More eval experimentation.** I got to 7/10 answer correctness and 90% retrieval hit rate, but there's a lot left to explore: different chunk sizes, top-k values, re-ranking, query expansion. I had one threshold (0.5 similarity gate) and one embedding model (`text-embedding-3-small`). A proper ablation study — holding everything else fixed and varying one parameter — would have produced much more meaningful benchmark results.

**The parser needed more investigation upfront.** The financial table formatting bug (currency symbols extracted as separate cells, column headers outside the detected table region) caused two persistent retrieval failures. A 20-line debug script caught it immediately. I should have run that script at the start of the project, not the end.

**No frontend.** The interactive CLI (`ask.py`) works, but a simple web UI showing retrieved sources alongside the answer — with similarity scores highlighted — would have made the system much more compelling to demo. This was always on the roadmap; I just ran out of time.

## What I Learned That I Didn't Expect

NVIDIA's FY2025 10-K doesn't report "Data Center" and "Gaming" as its primary financial segments — it uses "Compute & Networking" and "Graphics." The product-level breakdown (Data Center: $115.2B, Gaming: $11.4B) exists on a single page deep in the footnotes. The eval framework surfaced this mismatch automatically, which is exactly what a good eval system is supposed to do.

## What's Next

This project continues into summer. The roadmap includes JWT auth with row-level security, a Next.js dashboard with latency/accuracy/cost metrics, XBRL integration for structured financial data, and expanding the eval corpus to Microsoft's 10-K. The benchmarking infrastructure built here will be the foundation for all of it.
