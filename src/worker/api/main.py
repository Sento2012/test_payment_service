from contextlib import asynccontextmanager

from fastapi import FastAPI

from di.container import get_container
from infrastructure.Persistence import dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # API не публикует в брокер напрямую — только пишет в outbox (через БД),
    # поэтому подключение к RabbitMQ здесь не нужно.
    yield
    await dispose_engine()


app = FastAPI(
    title="Payment Processing Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(get_container().api_router())


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
