import json
import asyncpg
from openai import AsyncOpenAI
from ingestion.chunker import Chunk

EMBEDDING_MODEL = "text-embedding-3-small"


async def save_document(pool: asyncpg.Pool, filename: str, company: str, fiscal_year: str) -> str:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO documents (filename, company, fiscal_year)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            filename, company, fiscal_year,
        )
        return str(row["id"])


async def save_chunks(
    pool: asyncpg.Pool,
    document_id: str,
    embedded_chunks: list[tuple[Chunk, list[float]]],
    user_id: str = "default",
) -> None:
    records = [
        (
            document_id,
            user_id,
            chunk.text,
            str(embedding),
            json.dumps(chunk.metadata),
        )
        for chunk, embedding in embedded_chunks
    ]

    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO document_chunks (document_id, user_id, chunk_text, embedding, metadata)
            VALUES ($1, $2, $3, $4::vector, $5::jsonb)
            """,
            records,
        )


async def search_chunks(
    pool: asyncpg.Pool,
    query: str,
    document_id: str | None = None,
    user_id: str = "default",
    top_k: int = 5,
    min_similarity: float = 0.5,
) -> list[dict]:
    client = AsyncOpenAI(timeout=30.0)
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
    query_vector = str(response.data[0].embedding)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH ranked AS (
                SELECT chunk_text, metadata,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM document_chunks
                WHERE user_id = $2
                  AND ($3::uuid IS NULL OR document_id = $3::uuid)
                ORDER BY embedding <=> $1::vector
                LIMIT $4
            )
            SELECT * FROM ranked WHERE similarity >= $5
            """,
            query_vector, user_id, document_id, top_k, min_similarity,
        )

    return [
        {
            "chunk_text": row["chunk_text"],
            "metadata": json.loads(row["metadata"]),
            "similarity": float(row["similarity"]),
        }
        for row in rows
    ]
