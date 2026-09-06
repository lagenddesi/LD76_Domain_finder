from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import (
    APP_DEBUG,
    APP_ENV,
    APP_NAME,
    CORS_ORIGINS,
    validate_security_config,
)
from .database import Base, engine
from .rate_limit import limiter
from .routers import rescan, results, scans, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_security_config()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=APP_NAME,
    version="1.0.0",
    description=(
        "Secure backend API for the LD76 Domain Finder "
        "defensive web research platform."
    ),
    debug=APP_DEBUG,
    lifespan=lifespan,
)


app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Android-API-Key",
    ],
)


app.include_router(results.router)
app.include_router(scans.router)
app.include_router(rescan.router)
app.include_router(stats.router)


@app.get("/")
@limiter.limit("30/minute")
def root(request: Request):
    return {
        "name": APP_NAME,
        "environment": APP_ENV,
        "status": "online",
    }


@app.get("/health")
@limiter.limit("60/minute")
def health(request: Request):
    return {
        "status": "healthy",
        "service": "ld76-domain-finder-api",
    }
