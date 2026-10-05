from collections import deque
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request


def rate_limit(max_requests: int, window_seconds: int):
    requests_by_key: dict[str, deque[float]] = {}
    lock = Lock()

    def check_rate_limit(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        key = f"{route_path}:{client_ip}"
        now = monotonic()
        cutoff = now - window_seconds

        with lock:
            requests = requests_by_key.setdefault(key, deque())
            while requests and requests[0] <= cutoff:
                requests.popleft()

            if len(requests) >= max_requests:
                retry_after = max(1, ceil(window_seconds - (now - requests[0])))
                raise HTTPException(
                    status_code=429,
                    detail="Quá nhiều yêu cầu. Vui lòng thử lại sau.",
                    headers={"Retry-After": str(retry_after)},
                )

            requests.append(now)

            if len(requests_by_key) > 4096:
                expired_keys = [
                    request_key
                    for request_key, timestamps in requests_by_key.items()
                    if not timestamps or timestamps[-1] <= cutoff
                ]
                for request_key in expired_keys:
                    requests_by_key.pop(request_key, None)

    return check_rate_limit