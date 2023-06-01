import os
import atexit

from bson import ObjectId
from flask import Flask, jsonify
from pymongo import MongoClient

from fastapi import FastAPI, status, HTTPException

app = FastAPI()

mongo_url = os.environ['DB_URL']

client = MongoClient(mongo_url)
db = client["wdm"]
stock = db["stock"]


def close_db_connection():
    client.close()


atexit.register(close_db_connection)


@app.get('/', status_code=status.HTTP_200_OK)
def index():
    return "Health check"

@app.post('/item/create/{price}', status_code=status.HTTP_200_OK)
def create_item(price: int):
    document = {"price": price, "stock": 0}
    inserted_id = stock.insert_one(document).inserted_id
    return {"item_id": str(inserted_id)}


@app.get('/find/{item_id}', status_code=status.HTTP_200_OK)
def find_item(item_id: str):
    try:
        item = stock.find_one({"_id": ObjectId(item_id)})
        if item:
            item["_id"] = str(item["_id"])
            return item
        else:
            raise HTTPException(status_code=404, detail="Item not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=e)


@app.post('/add/{item_id}/{amount}', status_code=status.HTTP_200_OK)
def add_stock(item_id: str, amount: int):
    try:
        amount = int(amount)
        result = stock.update_one({"_id": ObjectId(item_id)}, {
                                  "$inc": {"stock": amount}})
        if result.matched_count > 0:
            return {"Success": True}
        else:
            raise HTTPException(status_code=404, detail="Item not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=e)


@app.post('/subtract/{item_id}/{amount}', status_code=status.HTTP_200_OK)
def remove_stock(item_id: str, amount: int):
    try:
        amount = int(amount)
        result = stock.update_one({"_id": ObjectId(item_id), "stock": {
                                  "$gte": amount}}, {"$inc": {"stock": -amount}})
        if result.matched_count > 0:
            return {"Success": True}
        else:
            raise HTTPException(status_code=400, detail="Item not found or not enough stock")
    except Exception as e:
        raise HTTPException(status_code=404, detail=e)
