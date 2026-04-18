from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Tuple

from fastapi import HTTPException, status


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    """Simple in-memory token bucket rate limiter.

    Note: In production you'd typically use Redis. This is good enough for local/dev and
    single-process deployments.
    """

    def __init__(self):
        self._buckets: Dict[str, _Bucket] = {}

    def hit(self, key: str, *, capacity: int, refill_per_sec: float) -> Tuple[bool, float]:
        now = time.time()
        bucket = self._buckets.get(key)
        if not bucket:
            bucket = _Bucket(tokens=float(capacity), last_refill=now)
            self._buckets[key] = bucket

        # Refill tokens
        elapsed = max(0.0, now - bucket.last_refill)
        bucket.tokens = min(float(capacity), bucket.tokens + elapsed * refill_per_sec)
        bucket.last_refill = now

        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True, 0.0

        # How long until 1 token
        needed = 1.0 - bucket.tokens
        retry_after = needed / refill_per_sec if refill_per_sec > 0 else 60.0
        return False, retry_after


rate_limiter = RateLimiter()


def rate_limit_or_429(key: str, *, capacity: int, refill_per_sec: float):
    ok, retry_after = rate_limiter.hit(key, capacity=capacity, refill_per_sec=refill_per_sec)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )
