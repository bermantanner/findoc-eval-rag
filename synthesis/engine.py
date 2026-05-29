import json
from openai import AsyncOpenAI

SYNTHESIS_MODEL = "gpt-4o"
SYSTEM_PROMPT = (
    "You are a financial analyst assistant. Answer the question using ONLY the provided "
    "context snippets from SEC 10-K filings. Be precise with numbers and cite the fiscal year "
    "when relevant. If the answer cannot be explicitly found in the provided context snippets, "
    "output exactly: 'Insufficient data in source document.' Do not attempt to guess."
)


def _build_context(chunks: list[dict]) -> str:
    return "\n\n---\n\n".join(
        f"[Source {i + 1} | Page {c['metadata'].get('page_number')} | "
        f"{c['metadata'].get('company')} {c['metadata'].get('fiscal_year')}]\n{c['chunk_text']}"
        for i, c in enumerate(chunks)
    )


def _format_plain(answer: str, chunks: list[dict]) -> str:
    lines = ["=" * 60, "ANSWER", "=" * 60, answer.strip(), "", "=" * 60, "SOURCES", "=" * 60]
    for i, c in enumerate(chunks):
        m = c["metadata"]
        snippet = c["chunk_text"].replace("\n", " ").strip()[:200]
        lines += [
            f"[{i + 1}] {m.get('company')} {m.get('fiscal_year')} — "
            f"Page {m.get('page_number')} (similarity: {c['similarity']:.2f})",
            f"    ...{snippet}...",
            "",
        ]
    return "\n".join(lines)


async def stream_answer(query: str, chunks: list[dict]):
    client = AsyncOpenAI(timeout=15.0)

    stream = await client.chat.completions.create(
        model=SYNTHESIS_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{_build_context(chunks)}\n\nQuestion: {query}"},
        ],
        stream=True,
    )

    async for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"

    yield f"data: {json.dumps({'type': 'source_nodes', 'chunks': chunks})}\n\n"
    yield "data: [DONE]\n\n"


async def plain_answer(query: str, chunks: list[dict]) -> str:
    client = AsyncOpenAI(timeout=15.0)

    response = await client.chat.completions.create(
        model=SYNTHESIS_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{_build_context(chunks)}\n\nQuestion: {query}"},
        ],
    )

    answer = response.choices[0].message.content
    return _format_plain(answer, chunks)
