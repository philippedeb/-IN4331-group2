import os
import redis.asyncio as redis
import asyncio
import json

redis_url = os.environ['DB_URL']

class AsyncRedisLogger:
    def __init__(self):
        self.redis = None

    async def connect(self):
        self.redis = await redis.Redis.from_url(redis_url)
        self.redis = await self.redis.connect()

    async def log(self, level, saga_id, service, action, state, message=""):
        if not self.redis:
            await self.connect()
        log_entry = {
            "level": level,
            "saga_id": saga_id,
            "service": service,
            "action": action,
            "state": state,
            "message": message
        }
        await self.redis.rpush("saga_logs", json.dumps(log_entry))

    async def get_logs(self):
        if not self.redis:
            await self.connect()
        logs = []
        length = await self.redis.llen("saga_logs")
        for i in range(length):
            log_entry = await self.redis.lindex("saga_logs", i)
            logs.append(json.loads(log_entry))
        return logs

    async def close(self):
        self.redis.close()
