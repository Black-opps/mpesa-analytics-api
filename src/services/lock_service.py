# src/services/lock_service.py - NEW

import logging
import uuid
from contextlib import contextmanager
from typing import Generator

import redis

logger = logging.getLogger(__name__)


class LockService:
    """Distributed lock service using Redis"""

    def __init__(self):
        self.redis = redis.Redis.from_url("redis://localhost:6379/0")
        self.default_timeout = 300

    @contextmanager
    def with_lock(
        self, lock_key: str, timeout: int = None
    ) -> Generator[bool, None, None]:
        """Context manager for distributed lock"""
        lock_id = str(uuid.uuid4())
        acquired = self.redis.set(
            f"lock:{lock_key}",
            lock_id,
            nx=True,
            ex=timeout or self.default_timeout,
        )

        if not acquired:
            logger.warning(f"Could not acquire lock: {lock_key}")
            yield False
            return

        try:
            yield True
        finally:
            script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            self.redis.eval(script, 1, f"lock:{lock_key}", lock_id)
