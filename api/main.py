import os
import tempfile
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.middleware import AuthMiddleware
from ingestion.parser import parse_pdf
from ingestion.chunker import chunk_blocks
from ingestion.vectorizer import embed_chunks
from retrieval.vector_store import save_document, save_chunks, search_chunks
from synthesis.engine import stream_answer, generate_answer


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    yield
    await app.state.db.close()


app = FastAPI(title="FinDoc-Eval API", lifespan=lifespan)
app.add_middleware(AuthMiddleware)


@app.get("/health")
async def health():
    async with app.state.db.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok"}


@app.post("/api/v1/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    company: str = Form(...),
    fiscal_year: str = Form(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are supported.")

    content = await file.read()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        try:
            blocks = parse_pdf(tmp_path)
        except ValueError as e:
            raise HTTPException(status_code=415, detail=str(e))

        chunks = chunk_blocks(blocks, company=company, fiscal_year=fiscal_year)
        embedded = await embed_chunks(chunks)
        document_id = await save_document(request.app.state.db, file.filename, company, fiscal_year)
        await save_chunks(request.app.state.db, document_id, embedded)

    finally:
        os.unlink(tmp_path)

    return {"document_id": document_id, "chunks_stored": len(embedded)}


class QueryRequest(BaseModel):
    query: str
    document_id: Optional[str] = None

class ChunkOut(BaseModel):
    text: str
    similarity: float
    page: int | None = None
    company: str | None = None
    fiscal_year: str | None = None
    block_type: str | None = None

class QueryResponse(BaseModel):
    query: str
    document_id: str | None = None
    answer: str
    chunks: list[ChunkOut]

def _to_chunk_out(c: dict) -> dict:
    """Translate a nested search_chunks row into the flat public API shape."""
    m = c["metadata"]
    return {
        "text": c["chunk_text"],
        "similarity": c["similarity"],
        "page": m.get("page_number"),
        "company": m.get("company"),
        "fiscal_year": m.get("fiscal_year"),
        "block_type": m.get("block_type"),
    }

@app.post("/api/v1/query", response_model=QueryResponse)
async def query_document(request: Request, body: QueryRequest, stream: bool = False):
    rows = await search_chunks(
        request.app.state.db,
        query=body.query,
        document_id=body.document_id,
    )
    chunks = [_to_chunk_out(c) for c in rows]

    if not chunks:
        return QueryResponse(
            query=body.query,
            document_id=body.document_id,
            answer="Insufficient data in source document.",
            chunks=[],
        )

    if stream:
        return StreamingResponse(
            stream_answer(body.query, chunks),
            media_type="text/event-stream",
        )

    answer = await generate_answer(body.query, chunks)
    return QueryResponse(
        query=body.query,
        document_id=body.document_id,
        answer=answer,
        chunks=chunks,
    )