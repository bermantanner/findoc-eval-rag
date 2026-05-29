from openai import AsyncOpenAI
from ingestion.chunker import Chunk

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 512


async def embed_chunks(chunks: list[Chunk]) -> list[tuple[Chunk, list[float]]]:
    client = AsyncOpenAI(timeout=30.0)
    results = []

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[c.text for c in batch],
        )
        for chunk, obj in zip(batch, response.data):
            results.append((chunk, obj.embedding))

    return results
