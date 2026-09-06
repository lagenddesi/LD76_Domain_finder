from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import (
    APP_DEBUG,
    APP_ENV,
    APP_NAME,
    CORS_ORIGINS,
    validate_security_config,
)
from .database import Base, engine
from .routers import results, scans


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


@app.get("/")
def root():
    return {
        "name": APP_NAME,
        "environment": APP_ENV,
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "ld76-domain-finder-api",
    }
