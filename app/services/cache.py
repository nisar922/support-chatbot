import hashlib
import json
import redis
from app.config import settings

CACHE_TTL_SECONDS = 3600
VERSION_KEY = "kb_version"

_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)

def get_client() -> redis.Redis:
    return _client

def _key(question: str) -> str:
    version = _client.get(VERSION_KEY) or "0"
    normalized = " ".join(question.lower().split())
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"answer:{version}:{digest}"

def get_cached_answer(question: str):
    try:
        value = _client.get(_key(question))
        return json.loads(value) if value else None
    except redis.RedisError:
        return None

def set_cached_answer(question: str, reply: str, resolved: bool) -> None:
    try:
        _client.set(
            _key(question),
            json.dumps({"reply": reply, "resolved": resolved}),
            ex=CACHE_TTL_SECONDS,
        )
    except redis.RedisError:
        pass

def invalidate_answers() -> None:
    try:
        _client.incr(VERSION_KEY)
    except redis.RedisError:
        pass