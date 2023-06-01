import json
import os
import atexit

from bson import ObjectId
from flask import Flask, jsonify
from pymongo import MongoClient
import pika

app = Flask("stock-service")

mongo_url = os.environ['DB_URL']

client = MongoClient(mongo_url)
db = client["wdm"]
stock = db["stock"]

connection = pika.BlockingConnection(pika.ConnectionParameters(host='in4331-group2_rabbitmq_1', port=5672, heartbeat=30))
channel = connection.channel()
# Create a queue for receiving responses from the stock and payment services
queue = channel.queue_declare(queue='stock').method.queue


def close_db_connection():
    client.close()


atexit.register(close_db_connection)


@app.get('/')
def index():
    return "Health check", 200


@app.post('/item/create/<price>')
def create_item(price: int):
    document = {"price": price, "stock": 0}
    inserted_id = stock.insert_one(document).inserted_id
    return jsonify({"item_id": str(inserted_id)}), 200


@app.get('/find/<item_id>')
def find_item(item_id: str):
    try:
        item = stock.find_one({"_id": ObjectId(item_id)})
        if item:
            item["_id"] = str(item["_id"])
            return jsonify(item), 200
        else:
            return jsonify({"Error": "Item not found"}), 404
    except Exception as e:
        return jsonify({"Error": str(e)}), 400


@app.post('/add/<item_id>/<amount>')
def add_stock(item_id: str, amount: int):
    try:
        amount = int(amount)
        result = stock.update_one({"_id": ObjectId(item_id)}, {
            "$inc": {"stock": amount}})
        if result.matched_count > 0:
            return jsonify({"Success": True}), 200
        else:
            return jsonify({"Error": "Item not found"}), 404
    except Exception as e:
        return jsonify({"Error": str(e)}), 400


def remove_stock(item_id: str, amount: int):
    try:
        amount = int(amount)
        result = stock.update_one({"_id": ObjectId(item_id), "stock": {
            "$gte": amount}}, {"$inc": {"stock": -amount}})
        if result.matched_count > 0:
            return jsonify({"Success": True}), 200
        else:
            return jsonify({"Error": "Item not found or not enough stock"}), 400
    except Exception as e:
        return jsonify({"Error": str(e)}), 400


def callback(ch, method, properties, body):
    json_body = json.loads(body)

    message_type = properties.headers.get('message_type')
    if message_type == 'decrease_stock_action':
        remove_stock(json_body['item_id'], json_body['amount'])
    elif message_type == 'decrease_stock_compensation':
        remove_stock(json_body['item_id'], - json_body['amount'])


channel.basic_consume(
    queue=queue, on_message_callback=callback, auto_ack=True)
