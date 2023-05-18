import os
import atexit

from bson import ObjectId
from flask import Flask, jsonify
from pymongo import MongoClient


app = Flask("stock-service")

mongo_url = os.environ['DB_URL']

client = MongoClient(mongo_url)
db = client["wdm"]
stock = db["stock"]


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


@app.post('/subtract/<item_id>/<amount>')
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
