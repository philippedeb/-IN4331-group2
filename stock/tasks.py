import atexit
import os
import sys

from bson import ObjectId
from pymongo import MongoClient
from celery import Celery

class CeleryConfig:
    # Celery configuration
    # http://docs.celeryproject.org/en/latest/configuration.html

    broker_url = os.environ.get('STOCK_BROKER_URL', '')
    result_backend = 'rpc://'

    # json serializer is more secure than the default pickle
    task_serializer = 'json'
    result_serializer = 'json'
    accept_content = ['json']

    # Use UTC instead of localtime
    enable_utc = True

app = Celery()
app.config_from_object(CeleryConfig)

IN_CELERY_WORKER_PROCESS = sys.argv and sys.argv[0].endswith('celery')\
    and 'worker' in sys.argv

if IN_CELERY_WORKER_PROCESS:
    print ('Im in Celery worker')
    mongo_url = os.environ['DB_URL']

    client = MongoClient(mongo_url)
    db = client["wdm"]
    stock = db["stock"]


    def close_db_connection():
        client.close()


    atexit.register(close_db_connection)


@app.task
def create_item(price: int):
    document = {"price": price, "stock": 0}
    inserted_id = stock.insert_one(document).inserted_id
    return {"item_id": str(inserted_id)}


@app.task
def find_item(item_id: str):
    try:
        item = stock.find_one({"_id": ObjectId(item_id)})
        if item:
            item["_id"] = str(item["_id"])
            return item
        else:
            return None
    except Exception as e:
        return None


@app.task
def add_stock(item_id: str, amount: int):
    try:
        amount = int(amount)
        result = stock.update_one({"_id": ObjectId(item_id)}, {
                                  "$inc": {"stock": amount}})
        if result.matched_count > 0:
            return {"success": True}
        else:
            return None
    except Exception as e:
        return None


@app.task
def remove_stock(item_id: str, amount: int):
    try:
        amount = int(amount)
        result = stock.update_one({"_id": ObjectId(item_id), "stock": {
                                  "$gte": amount}}, {"$inc": {"stock": -amount}})
        if result.matched_count > 0:
            return {"success": True}
        else:
            return None
    except Exception as e:
        return None
