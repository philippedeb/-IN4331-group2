import asyncio
import os
import atexit

from flask import Flask, jsonify, request
from logger import AsyncRedisLogger

app = Flask("logging-service")

logger = AsyncRedisLogger()

def close_redis_connection():
    logger.close()

atexit.register(close_redis_connection)

@app.route('/')
def index():
    return "Health check", 200

@app.route('/log', methods=['POST'])
def log_event():
    try:
        data = request.get_json()
        level = data.get('level')
        saga_id = data.get('saga_id')
        service = data.get('service')
        action = data.get('action')
        state = data.get('state')
        message = data.get('message', "")

        # Enqueue the logging task and continue handling the request
        asyncio.create_task(logger.log(level, saga_id, service, action, state, message))

        return jsonify({"Success": True}), 200
    except Exception as e:
        return jsonify({"Error": str(e)}), 400