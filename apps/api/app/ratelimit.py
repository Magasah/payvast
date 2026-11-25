"""Rate limiting.

Storage is in-process memory: the client IP lives only in RAM for the length of the window
and is never written to the database or logs (no-logs principle). With several API workers
this needs a shared store (Redis) — not part of the agreed stack yet.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

limiter = Limiter(
    key_func=get_remote_address,
    enabled=get_settings().rate_limit_enabled,
    headers_enabled=False,
)
