import os
import atexit

from bson import ObjectId
from flask import Flask, jsonify
from pymongo import MongoClient
import requests


gateway_url = os.environ['GATEWAY_URL']

app = Flask("order-service")

mongo_url = ""

client = MongoClient(mongo_url, ssl=True, tlsAllowInvalidCertificates=True)
db = client["wdm"]
orders = db["orders"]

def close_db_connection():
    client.close()

def close_db_connection():
    db.close()


atexit.register(close_db_connection)


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
    result = orders.update_one({"_id": ObjectId(order_id)}, {"$addToSet": {"items": item_id}})
    if result.matched_count > 0:
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "Order not found"}), 404


@app.delete('/removeItem/<order_id>/<item_id>')
def remove_item(order_id, item_id):
    result = orders.update_one({"_id": ObjectId(order_id)}, {"$pull": {"items": item_id}})
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
        total_cost = 0
        for item_id in items:
            item = requests.get(f"{gateway_url}/stock-service/find/{item_id}").json()
            total_cost += item["price"]
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
        items_subtracted = []

        for item_id in order["items"]:
            item = requests.get(f"{gateway_url}/stock-service/find/{item_id}").json()
            total_cost += item["price"]
            response = requests.post(f"{gateway_url}/stock-service/subtract/{item_id}/{1}")
            if response.status_code != 200:
                break
            items_subtracted.append(item_id)
        
        if (len(items_subtracted) != len(order["items"])):
            for item_id in items_subtracted:
                requests.post(f"{gateway_url}/stock-service/add/{item_id}/{1}")
            return jsonify({"Error": f"Item {item_id} is out of stock"})

        response = requests.post(f"{gateway_url}/payment-service/pay/{user_id}/{order_id}/{total_cost}")
        if response.status_code == 200:
            orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"paid": True}})
            return jsonify({"Success": True}), 200
        else:
            return jsonify({"Error": "Not enough credit or user not found"}), 400
    else:
        return jsonify({"Error": "Order not found"}), 404
