import redis
import json
from typing import Optional, Dict, Any

class RedisManager:
    def __init__(self, redis_url: str):
        self.client = redis.Redis.from_url(redis_url)
    
    def cache_application_state(self, app_name: str, state: Dict[str, Any], ttl: int = 3600):
        """Cache application state with expiration"""
        self.client.setex(
            f"app:{app_name}:state",
            ttl,
            json.dumps(state)
        )
    
    def get_cached_state(self, app_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached application state"""
        cached = self.client.get(f"app:{app_name}:state")
        return json.loads(cached) if cached else None
    
    def acquire_lock(self, lock_name: str, ttl: int = 30) -> bool:
        """Distributed lock implementation"""
        return bool(
            self.client.set(
                f"lock:{lock_name}",
                "1",
                nx=True,
                ex=ttl
            )
        )
    
    def release_lock(self, lock_name: str):
        """Release distributed lock"""
        self.client.delete(f"lock:{lock_name}")