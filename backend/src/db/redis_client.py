from redis import Redis
from typing import Any, Optional

class RedisClient:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.redis = Redis(host=host, port=port, db=db)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> None:
        self.redis.set(key, value, ex=ex)

    def get(self, key: str) -> Optional[str]:
        return self.redis.get(key)

    def delete(self, key: str) -> None:
        self.redis.delete(key)

    def exists(self, key: str) -> bool:
        return self.redis.exists(key) > 0

    def close(self) -> None:
        self.redis.close()