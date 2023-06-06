import os
import redis.asyncio as redis
import json

redis_url = os.environ['LOGGER_DB_URL']

class AsyncRedisLogger:
    def __init__(self):
        self.redis = None

    async def connect(self):
        self.redis = await redis.Redis.from_url(redis_url)
        self.redis = await self.redis.connect()

    async def log(self, saga_id, service, state):
        if not self.redis:
            await self.connect()
        log_entry = {
            "saga_id": saga_id,
            "service": service,
            "state": state
        }
        print("logging")
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
    
    async def update_log_state(self, saga_id, new_state):
        if not self.redis:
            await self.connect()
        length = await self.redis.llen("saga_logs")
        for i in range(length):
            log_entry = await self.redis.lindex("saga_logs", i)
            log = json.loads(log_entry)
            if log["saga_id"] == saga_id:
                log["state"] = new_state
                await self.redis.lset("saga_logs", i, json.dumps(log))
                return
        raise ValueError(f"No log found with saga_id {saga_id}")

    async def close(self):
        self.redis.close()