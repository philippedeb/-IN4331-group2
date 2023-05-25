import os
import atexit

from bson import ObjectId
from flask import Flask, jsonify
from pymongo import MongoClient
import json
import pika
import requests

from saga import Saga, State
import asyncio

payment_url = os.environ['PAYMENT_URL']
stock_url = os.environ['STOCK_URL']
payment_conn = pika.BlockingConnection(pika.ConnectionParameters(host='in4331-group2_rabbitmq_1', port=5672))
stock_conn = pika.BlockingConnection(pika.ConnectionParameters(host='in4331-group2_rabbitmq_1', port=5672))
payment_channel = payment_conn.channel()
stock_channel = stock_conn.channel()
stock_channel.exchange_declare(exchange='add', exchange_type='fanout')
app = Flask("order-service")

mongo_url = os.environ['DB_URL']

client = MongoClient(mongo_url)
db = client["wdm"]
orders = db["orders"]


def close_db_connection():
    client.close()


atexit.register(close_db_connection)


@app.get('/')
def index():
    return "Health check", 200


@app.post('/create/<user_id>')
def create_order(user_id):
    order = {"user_id": user_id, "items": [], "paid": False}
    inserted_id = orders.insert_one(order).inserted_id
    return jsonify({"order_id": str(inserted_id)}), 200


@app.delete('/remove/<order_id>')
def remove_order(order_id):
    result = orders.delete_one({"_id": ObjectId(order_id)})
    if result.deleted_count > 0:
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "Order not found"}), 404


@app.post('/addItem/<order_id>/<item_id>')
def add_item(order_id, item_id):
    result = orders.update_one({"_id": ObjectId(order_id)}, {
        "$addToSet": {"items": item_id}})
    if result.matched_count > 0:
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "Order not found"}), 404


@app.delete('/removeItem/<order_id>/<item_id>')
def remove_item(order_id, item_id):
    result = orders.update_one({"_id": ObjectId(order_id)}, {
        "$pull": {"items": item_id}})
    if result.matched_count > 0:
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "Order not found"}), 404


@app.get('/find/<order_id>')
def find_order(order_id):
    order = orders.find_one({"_id": ObjectId(order_id)})
    if order:
        order["_id"] = str(order["_id"])
        items = order["items"]
        app.logger.error(items)
        total_cost = 0
        for item_id in items:
            item = requests.get(f"{stock_url}/find/{item_id}").json()
            app.logger.error(item)
            total_cost += float(item["price"])
        order["total_cost"] = total_cost
        return jsonify(order), 200
    else:
        return jsonify({"Error": "Order not found"}), 404


@app.post('/checkout/<order_id>')
def checkout(order_id):
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

        asyncio.run(saga.run())

        if saga.state == State.SUCCESS:
            return jsonify({"Success": True}), 200
        else:

            error = {}
            for step in saga.steps:
                error[step.name] = step.state.name
                app.logger.error(f"Step {step.name}: {step.state}")

            return jsonify({"Error": error}), 400

    else:
        return jsonify({"Error": "Order not found"}), 404


def decrease_stock_action(item_id):
    """Return coroutine function that decreases stock of item with given id by 1"""
    # stock_channel.basic_publish(exchange='remove', routing_key='', body=item_id)


def decrease_stock_compensation(item_id):
    """Return coroutine function that compensates the decrease_stock (increases stock of item with given id by 1)"""
    # stock_channel.basic_publish(exchange='add', routing_key='', body=item_id)


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
