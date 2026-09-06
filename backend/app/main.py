import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

Load environment variables from .env when running locally.

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "LD76 Domain Finder API")
APP_ENV = os.getenv("APP_ENV", "development")
APP_DEBUG = os.getenv("APP_DEBUG", "false").lower() == "true"

cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
CORS_ORIGINS = [
origin.strip()
for origin in cors_origins_raw.split(",")
if origin.strip()
]

app = FastAPI(
title=APP_NAME,
version="1.0.0",
description=(
"Secure backend API for the LD76 Domain Finder "
"defensive web research platform."
),
debug=APP_DEBUG,
)

app.add_middleware(
CORSMiddleware,
allow_origins=CORS_ORIGINS,
allow_credentials=False,
allow_methods=["GET", "POST"],
allow_headers=["Content-Type", "Authorization", "X-Android-API-Key"],
)

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
