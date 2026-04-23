from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import check_db_connection
from app.core.limiter import limiter
from app.core.redis import check_redis_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Flouze API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ──────────────────────────────────────────────────────────────────

from app.api.v1 import auth, categories, expenses, users  # noqa: E402

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(expenses.router, prefix="/api/v1")


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health():
    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()
    status_str = "ok" if (db_ok and redis_ok) else "degraded"
    return {
        "status": status_str,
        "db": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }
