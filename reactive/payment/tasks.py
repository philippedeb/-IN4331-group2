import atexit
import os
import sys

from bson import ObjectId
from pymongo import MongoClient
from celery import Celery

class CeleryConfig:
    # Celery configuration
    # http://docs.celeryproject.org/en/latest/configuration.html

    broker_url = os.environ.get('PAYMENT_BROKER_URL', '')
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
    payments = db["payments"]


    def close_db_connection():
        client.close()


    atexit.register(close_db_connection)


@app.task
def create_user():
    new_user = {"credit": 0}
    inserted_id = payments.insert_one(new_user).inserted_id
    return {"user_id": str(inserted_id)}


@app.task
def find_user(user_id: str):
    user = payments.find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
        return user
    else:
        return None


@app.task
def add_credit(user_id: str, amount: int):
    amount = int(amount)
    result = payments.update_one({"_id": ObjectId(user_id)}, {
                                 "$inc": {"credit": amount}})
    if result.matched_count > 0:
        return {"success": True}
    else:
        return None


@app.task
def remove_credit(user_id: str, order_id: str, amount: int):
    amount = int(amount)
    result = payments.update_one({"_id": ObjectId(user_id), "credit": {
                                 "$gte": amount}}, {"$inc": {"credit": -amount}})
    if result.matched_count > 0:
        payments.update_one({"_id": ObjectId(user_id)}, {
                            "$addToSet": {"paid_orders": order_id}})
        return {"success": True}
    else:
        return None


@app.task
def cancel_payment(user_id: str, order_id: str, amount: int):
    user = payments.find_one(
        {"_id": ObjectId(user_id), "paid_orders": order_id})
    if user:
        amount = int(amount)
        result = payments.update_one({"_id": ObjectId(user_id)}, {
                                     "$inc": {"credit": amount}, "$pull": {"paid_orders": order_id}})
        return {"success": True}
    else:
        return None


@app.task
def payment_status(user_id: str, order_id: str):
    user = payments.find_one({"_id": ObjectId(user_id)})
    if user:
        return {"paid": order_id in user.get("paid_orders", [])}
    else:
        return None
