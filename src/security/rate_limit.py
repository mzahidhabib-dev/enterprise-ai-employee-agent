# src/security/rate_limit.py
"""
Redis Rate Limiting utility.

Implements rate limiting for the incoming trigger endpoints and the
outgoing Gemini API calls using the Redis INCR + EXPIRE pattern.
"""

import os
import redis

class RateLimitError(Exception):
    """Raised when an internal agent action exceeds its rate limit."""
    pass

class RateLimiter:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        # decode_responses=True returns strings instead of bytes
        self.r = redis.from_url(redis_url, decode_responses=True)
        
    def check_and_increment(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Increments the counter for `key` and sets its expiry.
        Returns True if the limit has not been exceeded, False otherwise.
        """
        try:
            pipe = self.r.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            result, ttl = pipe.execute()
            
            # If it's a new key (result == 1) or TTL wasn't set (ttl == -1), set the expiration
            if result == 1 or ttl == -1:
                self.r.expire(key, window_seconds)
                
            return result <= limit
        except Exception as e:
            # If Redis connection fails, we log it but "fail open" so the agent doesn't crash completely.
            print(f"Redis rate limiter error: {e}")
            return True

# Singleton instance to use across nodes and FastAPI middleware
rate_limiter = RateLimiter()
