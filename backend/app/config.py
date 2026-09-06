import os

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


APP_NAME = os.getenv("APP_NAME", "LD76 Domain Finder API")
APP_ENV = os.getenv("APP_ENV", "development")
APP_DEBUG = _as_bool(os.getenv("APP_DEBUG", "false"))

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")
ANDROID_API_KEY = os.getenv("ANDROID_API_KEY", "")

CORS_ORIGINS = _as_list(
    os.getenv("CORS_ORIGINS", "http://localhost:3000")
)

SCANNER_SCRIPT = os.getenv(
    "SCANNER_SCRIPT",
    "scanner/scanner.py",
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
)


def validate_security_config() -> None:
    """Fail early when production security secrets are missing."""
    if APP_ENV.lower() == "production":
        if not API_SECRET_KEY:
            raise RuntimeError(
                "API_SECRET_KEY must be configured in production."
            )

        if not ANDROID_API_KEY:
            raise RuntimeError(
                "ANDROID_API_KEY must be configured in production."
            )
