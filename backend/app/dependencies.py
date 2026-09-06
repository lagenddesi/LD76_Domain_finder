from fastapi import Depends

from .security import require_android_api_key


def authenticated_client(
    api_key: str = Depends(require_android_api_key),
) -> str:
    """Dependency used by protected API endpoints."""
    return api_key
