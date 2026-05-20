# findoc-eval-rag
## Title:

FinDoc-Eval: Automated Benchmarking for Financial Document Retrieval

## One sentence description:

Intelligent search engine to query complex SEC financial filings, using custom automated Python test suite to measure and improve data retrieval accuracy (Ship with auth + live URL)

## Planned technologies:

For the backend I plan to use Python with FastAPI for handling the concurrent API requests and streaming text responses. For the database, I want to use PostgreSQL and an extension so I can store the app data and vector embeddings in the same place. For the LLM layer I probably will use Anthropic. For deployment, I'll do Docker containers hosted on AWS or. Vercel using a simple auth setup to keep user data separate.

## First deliverable:

I want to have a working backend API endpoint where an authenticated user can upload a single SEC 10-K financial PDF. System will extract the text, split it into chunks, generate embeddings, and save everything into the vector database. The user can then send a text question and get back the exact paragraphs needed to answer it.

## Rough architecture for the first deliverable:

The 5 core components im thinking are 
1. Auth Middleware (intercept incoming request to verify user tokens)
2. Ingestion & Parser pipeline (takes raw PDF, uses python libraries to pull out text while preserving layout of the financial tables)
3. Vectorization Engine (slices the processed text into chunks, passes them to embedding API, and gets back data vectors.
4. Retrieval Engine (takes user question, turns it into a vector, runs a similarity query against pgvector, and returns most relevant matching text snippets.
5. Synthesis Engine (packages the retrieved financial snippets alongside user's question into a clean prompt, hits LLM, streams final answer back)

## After first deliverable goals:

- The Testing Harness: I will write standalone python script with a fixed gold dataset of many complex numeric questions directly mapped to the real financial answers in the filings. 
- Retrieval Tuning: I'll implement and test different test splitting methods to raise test scores
- Developer dashboard: If there's time, a clean minimal TypeScript/Next.js dashboard that tracks the system metrics. (Im thinking like look-up speed, API costs, current accuracy?)
- Cost guardrails: If there's time, a simple Redis tool to log API usage per user, which blocks further queries if an account hits a safe monthly budget ceiling. (This is probably way out of scope, might add it in the summer)

