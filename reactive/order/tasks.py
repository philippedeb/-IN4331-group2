import atexit
import os
import sys

from bson import ObjectId
from pymongo import MongoClient
from celery import Celery

class CeleryConfig:
    # Celery configuration
    # http://docs.celeryproject.org/en/latest/configuration.html

    broker_url = os.environ.get('ORDER_BROKER_URL', '')
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
    orders = db["orders"]


    def close_db_connection():
        client.close()


    atexit.register(close_db_connection)


@app.task
def create_order(user_id):
    order = {"user_id": user_id, "items": [], "paid": False}
    inserted_id = orders.insert_one(order).inserted_id
    return {"order_id": str(inserted_id)}


@app.task
def remove_order(order_id):
    result = orders.delete_one({"_id": ObjectId(order_id)})
    if result.deleted_count > 0:
        return {"success": True}
    else:
        return None


@app.task
def add_item(order_id, item_id):
    result = orders.update_one({"_id": ObjectId(order_id)}, {
                               "$addToSet": {"items": item_id}})
    if result.matched_count > 0:
        return {"success": True}
    else:
        return None


@app.task
def remove_item(order_id, item_id):
    result = orders.update_one({"_id": ObjectId(order_id)}, {
                               "$pull": {"items": item_id}})
    if result.matched_count > 0:
        return {"success": True}
    else:
        return None


@app.get('/find/{order_id}', status_code=status.HTTP_200_OK)
def find_order(order_id):
    order = orders.find_one({"_id": ObjectId(order_id)})
    if order:
        order["_id"] = str(order["_id"])
        items = order["items"]
        print(items)
        total_cost = 0
        for item_id in items:
            item = requests.get(f"{stock_url}/find/{item_id}").json()
            print(item)
            total_cost += float(item["price"])
        order["total_cost"] = total_cost
        return order
    else:
        raise HTTPException(status_code=404, detail="Order not found")


@app.post('/checkout/{order_id}', status_code=status.HTTP_200_OK)
async def checkout(order_id):
    order = orders.find_one({"_id": ObjectId(order_id)})
    if order:
        user_id = order["user_id"]
        total_cost = 0
        saga = Saga()

        for item_id in order["items"]:
            item = requests.get(f"{stock_url}/find/{item_id}").json()
            total_cost += float(item["price"])

            # One saga step for each item to update
            saga.add_step(f"Decrease {item_id}", decrease_stock_action(
                item_id), decrease_stock_compensation(item_id))

        # One saga step for payment
        saga.add_step(f"Payment user {user_id}: {total_cost}", payment_action(
            user_id, order_id, total_cost), payment_compensation(user_id, order_id, total_cost))

        await saga.run()

        if saga.state == State.SUCCESS:
            return {"Success": True}
        else:

            error = {}
            for step in saga.steps:
                error[step.name] = step.state.name
                print(f"Step {step.name}: {step.state}")
            
            raise HTTPException(status_code=400, detail=error)

    else:
        raise HTTPException(status_code=404, detail="Order not found")


def decrease_stock_action(item_id):
    """Return coroutine function that decreases stock of item with given id by 1"""
    async def func():
        response = requests.post(f"{stock_url}/subtract/{item_id}/{1}")
        if response.status_code != 200:
            return False
        return True
    return func


def decrease_stock_compensation(item_id):
    """Return coroutine function that compensates the decrease_stock (increases stock of item with given id by 1)"""
    async def func():
        response = requests.post(f"{stock_url}/add/{item_id}/{1}")
        if response.status_code != 200:
            return False
        return True
    return func


def payment_action(user_id, order_id, total_cost):
    """Return coroutine function to deduct payment from user_id with total_cost, associated with order_id"""
    async def func():
        response = requests.post(
            f"{payment_url}/pay/{user_id}/{order_id}/{total_cost}")
        if response.status_code != 200:
            return False
        return True
    return func


def payment_compensation(user_id, order_id, total_cost):
    """Return coroutine function to compensate payment (add total_cost to user_i, associated with order_id"""
    async def func():
        response = requests.post(
            f"{payment_url}/cancel/{user_id}/{order_id}/{total_cost}")
        if response.status_code != 200:
            return False
        return True
    return func