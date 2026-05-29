import os
import tempfile
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile

from api.middleware import AuthMiddleware
from ingestion.parser import parse_pdf
from ingestion.chunker import chunk_blocks
from ingestion.vectorizer import embed_chunks
from retrieval.vector_store import save_document, save_chunks


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
