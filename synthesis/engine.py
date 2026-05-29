import json
from openai import AsyncOpenAI

SYNTHESIS_MODEL = "gpt-4o"
SYSTEM_PROMPT = (
    "You are a financial analyst assistant. Answer the question using ONLY the provided "
    "context snippets from SEC 10-K filings. Be precise with numbers and cite the fiscal year "
    "when relevant. If the answer cannot be explicitly found in the provided context snippets, "
    "output exactly: 'Insufficient data in source document.' Do not attempt to guess."
)


async def stream_answer(query: str, chunks: list[dict]):
    client = AsyncOpenAI(timeout=15.0)

    context = "\n\n---\n\n".join(
        f"[Source {i + 1} | Page {c['metadata'].get('page_number')} | "
        f"{c['metadata'].get('company')} {c['metadata'].get('fiscal_year')}]\n{c['chunk_text']}"
        for i, c in enumerate(chunks)
    )

    stream = await client.chat.completions.create(
        model=SYNTHESIS_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ],
        stream=True,
    )

    async for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"

    yield f"data: {json.dumps({'type': 'source_nodes', 'chunks': chunks})}\n\n"
    yield "data: [DONE]\n\n"
