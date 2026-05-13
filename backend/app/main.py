from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.config import settings
from app.db import Base, engine
from app.routers import drafts, export, feed, leads, sync
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Content Intel API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(drafts.router)
app.include_router(export.router)
app.include_router(feed.router)
app.include_router(leads.router)
app.include_router(sync.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
