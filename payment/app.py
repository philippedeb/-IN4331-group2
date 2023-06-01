import json
import os
import atexit

import pika
from bson import ObjectId
from flask import Flask, jsonify
from pymongo import MongoClient
import requests

app = Flask("payment-service")

mongo_url = os.environ['DB_URL']

client = MongoClient(mongo_url)
db = client["wdm"]
payments = db["payments"]

connection = pika.BlockingConnection(pika.ConnectionParameters(host='in4331-group2_rabbitmq_1', port=5672, heartbeat=30))
channel = connection.channel()
# Create a queue for receiving responses from the stock and payment services
queue = channel.queue_declare(queue='payment').method.queue


def close_db_connection():
    client.close()


atexit.register(close_db_connection)


@app.get('/')
def index():
    return "Health check", 200


@app.post('/create_user')
def create_user():
    new_user = {"credit": 0}
    inserted_id = payments.insert_one(new_user).inserted_id
    return jsonify({"user_id": str(inserted_id)}), 200


@app.get('/find_user/<user_id>')
def find_user(user_id: str):
    user = payments.find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
        return jsonify(user), 200
    else:
        return jsonify({"Error": "User not found"}), 404


@app.post('/add_funds/<user_id>/<amount>')
def add_credit(user_id: str, amount: float):
    amount = float(amount)
    result = payments.update_one({"_id": ObjectId(user_id)}, {
                                 "$inc": {"credit": amount}})
    if result.matched_count > 0:
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "User not found"}), 404


@app.post('/pay/<user_id>/<order_id>/<amount>')
def remove_credit(user_id: str, order_id: str, amount: float):
    amount = float(amount)
    result = payments.update_one({"_id": ObjectId(user_id), "credit": {
                                 "$gte": amount}}, {"$inc": {"credit": -amount}})
    if result.matched_count > 0:
        payments.update_one({"_id": ObjectId(user_id)}, {
                            "$addToSet": {"paid_orders": order_id}})
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "Not enough credit or user not found"}), 400


@app.post('/cancel/<user_id>/<order_id>/<amount>')
def cancel_payment(user_id: str, order_id: str, amount: float):
    user = payments.find_one(
        {"_id": ObjectId(user_id), "paid_orders": order_id})
    if user:
        amount = float(amount)
        result = payments.update_one({"_id": ObjectId(user_id)}, {
                                     "$inc": {"credit": amount}, "$pull": {"paid_orders": order_id}})
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "Payment not found"}), 404


@app.post('/status/<user_id>/<order_id>')
def payment_status(user_id: str, order_id: str):
    user = payments.find_one({"_id": ObjectId(user_id)})
    if user:
        return jsonify({"Paid": order_id in user.get("paid_orders", [])}), 200
    else:
        return jsonify({"Error": "User not found"}), 404


def callback(ch, method, properties, body):
    json_body = json.loads(body)
    remove_credit(json_body['user'], json_body['order_id'], json_body['amount'])


channel.basic_consume(
    queue=queue, on_message_callback=callback, auto_ack=True)
