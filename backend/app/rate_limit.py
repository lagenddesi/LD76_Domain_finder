from slowapi import Limiter
from slowapi.util import get_remote_address


# One shared limiter instance for the entire backend.
# This keeps rate-limit configuration consistent across
# the application and all API routers.
limiter = Limiter(
    key_func=get_remote_address,
)
