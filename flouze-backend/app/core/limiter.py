from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory for V1; swap storage_uri=settings.redis_url for Redis-backed limiting
limiter = Limiter(key_func=get_remote_address)
