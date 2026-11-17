from collections import deque
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request


def _client_ip(request: Request) -> str:
    """Lay IP thuc sau proxy tin cay; mac dinh dung IP ket noi truc tiep."""
    direct = request.client.host if request.client else "unknown"
    try:
        from app.core.config import settings
        trusted = set(settings.trusted_proxies_list)
    except Exception:
        return direct
    if direct not in trusted:
        return direct
    forwarded = request.headers.get("x-forwarded-for", "")
    first = forwarded.split(",")[0].strip() if forwarded else ""
    return first or direct


def _redis_client():
    """Tra ve Redis client neu co cau hinh REDIS_URL, nguoc lai None."""
    try:
        from app.core.config import settings
        url = (settings.REDIS_URL or "").strip()
        if not url:
            return None
        import redis
        return redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
    except Exception:
        return None


def _check_memory(key: str, max_requests: int, window_seconds: int, store: dict, lock: Lock) -> None:
    now = monotonic()
    cutoff = now - window_seconds
    with lock:
        requests = store.setdefault(key, deque())
        while requests and requests[0] <= cutoff:
            requests.popleft()
        if len(requests) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail="Quá nhiều yêu cầu. Vui lòng thử lại sau.",
                headers={"Retry-After": str(max(1, ceil(window_seconds - (now - requests[0]))))},
            )
        requests.append(now)
        if len(store) > 4096:
            for request_key in [k for k, v in store.items() if not v or v[-1] <= cutoff]:
                store.pop(request_key, None)


def _check_redis(client, key: str, max_requests: int, window_seconds: int) -> None:
    """Sliding-window bang ZSET; loi Redis thi cho qua de khong chan dich vu."""
    import time
    now_ms = int(time.time() * 1000)
    window_ms = window_seconds * 1000
    member = f"{now_ms}:{monotonic()}"
    pipe = client.pipeline()
    pipe.zremrangebyscore(key, 0, now_ms - window_ms)
    pipe.zadd(key, {member: now_ms})
    pipe.zcard(key)
    pipe.expire(key, window_seconds + 5)
    try:
        results = pipe.execute()
    except Exception:
        return
    count = results[2] if len(results) > 2 else 0
    if count > max_requests:
        oldest = client.zrange(key, 0, 0, withscores=True)
        retry_after = 1
        if oldest:
            retry_after = max(1, ceil(window_seconds - (now_ms - oldest[0][1]) / 1000))
        raise HTTPException(
            status_code=429,
            detail="Quá nhiều yêu cầu. Vui lòng thử lại sau.",
            headers={"Retry-After": str(retry_after)},
        )


def rate_limit(max_requests: int, window_seconds: int):
    requests_by_key: dict[str, deque[float]] = {}
    lock = Lock()

    def check_rate_limit(request: Request) -> None:
        client_ip = _client_ip(request)
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        key = f"ratelimit:{route_path}:{client_ip}"
        redis_client = _redis_client()
        if redis_client is not None:
            _check_redis(redis_client, key, max_requests, window_seconds)
        else:
            _check_memory(key, max_requests, window_seconds, requests_by_key, lock)

    return check_rate_limit