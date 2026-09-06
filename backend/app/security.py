import secrets

from fastapi import Header, HTTPException, status

from .config import ANDROID_API_KEY


def require_android_api_key(
    x_android_api_key: str | None = Header(default=None),
) -> str:
    """Validate the API key used by the Android client."""

    if not ANDROID_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Android API authentication is not configured.",
        )

    if not x_android_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key.",
        )

    if not secrets.compare_digest(
        x_android_api_key,
        ANDROID_API_KEY,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    return x_android_api_key
