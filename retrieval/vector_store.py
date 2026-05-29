import json
import asyncpg
from ingestion.chunker import Chunk


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
) -> None:
    records = [
        (
            document_id,
            "default",
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
