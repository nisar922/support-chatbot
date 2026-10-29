import redis
from fastapi import Depends, HTTPException
from app.deps import get_current_user
from app.models import User
from app.services.cache import get_client

CHAT_LIMIT = 10
WINDOW_SECONDS = 60

def rate_limit_chat(user: User = Depends(get_current_user)) -> None:
    key = f"ratelimit:chat:{user.id}"
    try:
        r = get_client()
        r.set(key, 0, ex=WINDOW_SECONDS, nx=True)
        count = r.incr(key)
        if count > CHAT_LIMIT:
            retry_after = max(r.ttl(key), 1)
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please slow down.",
                headers={"Retry-After": str(retry_after)},
            )
    except redis.RedisError:
        return