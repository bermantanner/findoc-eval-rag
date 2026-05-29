from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncpg
import os

from api.middleware import AuthMiddleware


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
