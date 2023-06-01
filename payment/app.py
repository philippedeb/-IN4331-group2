import os
import atexit

from bson import ObjectId
from flask import Flask, jsonify
from fastapi import FastAPI, status, HTTPException
from pymongo import MongoClient
import requests

app = FastAPI()

mongo_url = os.environ['DB_URL']

client = MongoClient(mongo_url)
db = client["wdm"]
payments = db["payments"]


def close_db_connection():
    client.close()


atexit.register(close_db_connection)


@app.get('/', status_code=status.HTTP_200_OK)
def index():
    return "Health check"

@app.post('/create_user', status_code=status.HTTP_200_OK)
def create_user():
    new_user = {"credit": 0}
    inserted_id = payments.insert_one(new_user).inserted_id
    return {"user_id": str(inserted_id)}


@app.get('/find_user/{user_id}', status_code=status.HTTP_200_OK)
def find_user(user_id: str):
    user = payments.find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
        return user
    else:
        raise HTTPException(status_code=404, detail="User not found")


@app.post('/add_funds/{user_id}/{amount}', status_code=status.HTTP_200_OK)
def add_credit(user_id: str, amount: float):
    amount = float(amount)
    result = payments.update_one({"_id": ObjectId(user_id)}, {
                                 "$inc": {"credit": amount}})
    if result.matched_count > 0:
        return {"Success": True}
    else:
        raise HTTPException(status_code=404, detail="User not found")


@app.post('/pay/{user_id}/{order_id}/{amount}', status_code=status.HTTP_200_OK)
def remove_credit(user_id: str, order_id: str, amount: float):
    amount = float(amount)
    result = payments.update_one({"_id": ObjectId(user_id), "credit": {
                                 "$gte": amount}}, {"$inc": {"credit": -amount}})
    if result.matched_count > 0:
        payments.update_one({"_id": ObjectId(user_id)}, {
                            "$addToSet": {"paid_orders": order_id}})
        return {"Success": True}
    else:
        raise HTTPException(status_code=400, detail="Not enough credit or user not found")


@app.post('/cancel/{user_id}/{order_id}/{amount}', status_code=status.HTTP_200_OK)
def cancel_payment(user_id: str, order_id: str, amount: float):
    user = payments.find_one(
        {"_id": ObjectId(user_id), "paid_orders": order_id})
    if user:
        amount = float(amount)
        result = payments.update_one({"_id": ObjectId(user_id)}, {
                                     "$inc": {"credit": amount}, "$pull": {"paid_orders": order_id}})
        return {"Success": True}
    else:
        raise HTTPException(status_code=404, detail="Payment not found")


@app.post('/status/{user_id}/{order_id}', status_code=status.HTTP_200_OK)
def payment_status(user_id: str, order_id: str):
    user = payments.find_one({"_id": ObjectId(user_id)})
    if user:
        {"Paid": order_id in user.get("paid_orders", [])}
    else:
        raise HTTPException(status_code=404, detail="User not found")
