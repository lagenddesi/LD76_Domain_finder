import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(file).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"

load_dotenv(BACKEND_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env")

def _as_bool(value, default=False):
if value is None:
return default
return value.strip().lower() in {"1", "true", "yes", "on"}

def _as_list(value):
if not value:
return []
return [item.strip() for item in value.split(",") if item.strip()]

def _as_int(value, default):
try:
return int(value) if value is not None else default
except (TypeError, ValueError):
return default

APP_NAME = os.getenv("APP_NAME", "LD76 Domain Finder API")
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
APP_DEBUG = _as_bool(os.getenv("APP_DEBUG"), False)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = _as_int(os.getenv("PORT"), 8000)

API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")
ANDROID_API_KEY = os.getenv("ANDROID_API_KEY", "")

CORS_ORIGINS = _as_list(
os.getenv("CORS_ORIGINS", "http://localhost:3000")
)

DATABASE_URL = os.getenv(
"DATABASE_URL",
"sqlite:///./ld76_domain_finder.db",
)

SCANNER_SCRIPT = os.getenv(
"SCANNER_SCRIPT",
"scanner/scanner.py",
)

PYTHON_MIN_SCORE = _as_int(
os.getenv("PYTHON_MIN_SCORE"),
60,
)

PYTHON_RESULT_SCORE = _as_int(
os.getenv("PYTHON_RESULT_SCORE"),
80,
)

PYTHON_GEMINI_THRESHOLD = _as_int(
os.getenv("PYTHON_GEMINI_THRESHOLD"),
80,
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

def resolve_project_path(value):
path = Path(value)

if path.is_absolute():
    return path.resolve()

return (PROJECT_ROOT / path).resolve()

def validate_security_config():
if APP_ENV == "production":
if not API_SECRET_KEY:
raise RuntimeError(
"API_SECRET_KEY must be configured in production."
)

    if len(API_SECRET_KEY) < 32:
        raise RuntimeError(
            "API_SECRET_KEY must be at least 32 characters."
        )

    if not ANDROID_API_KEY:
        raise RuntimeError(
            "ANDROID_API_KEY must be configured in production."
        )

    if len(ANDROID_API_KEY) < 16:
        raise RuntimeError(
            "ANDROID_API_KEY must be at least 16 characters."
        )

    if APP_DEBUG:
        raise RuntimeError(
            "APP_DEBUG must be false in production."
        )

if not CORS_ORIGINS:
    raise RuntimeError(
        "At least one CORS_ORIGINS value must be configured."
    )
