from flask import Flask, jsonify

from celery import group
import payment.tasks as payment
import stock.tasks as stock
import order.tasks as orders

from .saga import Saga, State

app = Flask("gateway-service")


@app.get('/')
def index():
    return "Health check", 200

@app.post('/payment/create_user')
def create_user():
    task = payment.create_user.delay()
    user = task.get()
    if user and not task.failed():
        return jsonify(user), 200
    else:
        return jsonify({"Error": "User not found"}), 404


@app.get('/payment/find_user/<user_id>')
def find_user(user_id: str):
    task = payment.find_user.delay(user_id)
    user = task.get()
    if user and not task.failed():
        return jsonify(user), 200
    else:
        return jsonify({"Error": "User not found"}), 404


@app.post('/payment/add_funds/<user_id>/<amount>')
def add_credit(user_id: str, amount: int):
    task = payment.add_credit.delay(user_id, amount)
    result = task.get()
    if result and not task.failed():
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "User not found"}), 404


@app.post('/payment/pay/<user_id>/<order_id>/<amount>')
def remove_credit(user_id: str, order_id: str, amount: int):
    task = payment.remove_credit.delay(user_id, amount)
    result = task.get()
    if result and not task.failed():
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "Not enough credit or user not found"}), 400


@app.post('/payment/cancel/<user_id>/<order_id>/<amount>')
def cancel_payment(user_id: str, order_id: str, amount: int):
    task = payment.cancel_payment.delay(user_id, amount)
    result = task.get()
    if result and not task.failed():
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "Payment not found"}), 404


@app.post('/payment/status/<user_id>/<order_id>')
def payment_status(user_id: str, order_id: str):
    task = payment.payment_status.delay(user_id, order_id)
    result = task.get()
    if result and not task.failed():
        return jsonify(result), 200
    else:
        return jsonify({"Error": "User not found"}), 404

@app.post('/stock/item/create/<price>')
def create_item(price: int):
    task = stock.create_item.delay(price)
    item = task.get()
    if item and not task.failed():
        return jsonify(item), 200
    else:
        return jsonify({"Error": "Error creating item"}), 500

@app.get('/stock/find/<item_id>')
def find_item(item_id: str):
    task = stock.find_item.delay(item_id)
    item = task.get()
    if item and not task.failed():
        return jsonify(item), 200
    else:
        return jsonify({"Error": "Item not found"}), 404


@app.post('/stock/add/<item_id>/<amount>')
def add_stock(item_id: str, amount: int):
    task = stock.add_stock.delay(item_id, amount)
    result = task.get()
    if result and not task.failed():
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "Item not found"}), 404

@app.post('/stock/subtract/<item_id>/<amount>')
def remove_stock(item_id: str, amount: int):
    task = stock.remove_stock.delay(item_id, amount)
    result = task.get()
    if result and not task.failed():
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "Not enough stock or item not found"}), 400
    
@app.post('/orders/create/<user_id>')
def create_order(user_id):
    task = orders.create_order.delay(user_id)
    order = task.get()
    if order and not task.failed():
        return jsonify(order), 200
    else:
        return jsonify({"Error": "Error creating order"}), 500


@app.delete('/orders/remove/<order_id>')
def remove_order(order_id):
    task = orders.remove_order.delay(order_id)
    result = task.get()
    if result and not task.failed():
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "Order not found"}), 404

@app.post('/orders/addItem/<order_id>/<item_id>')
def add_item(order_id, item_id):
    task = orders.add_item.delay(order_id, item_id)
    result = task.get()
    if result and not task.failed():
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "Order not found"}), 404


@app.delete('/orders/removeItem/<order_id>/<item_id>')
def remove_item(order_id, item_id):
    task = orders.remove_item.delay(order_id, item_id)
    result = task.get()
    if result and not task.failed():
        return jsonify({"Success": True}), 200
    else:
        return jsonify({"Error": "Order not found"}), 404

@app.get('/orders/find/<order_id>')
def find_order(order_id):
    task = orders.find_order.delay(order_id)
    order = task.get()
    
    if order:
        items = order["items"]
        items_task = group([stock.find_item.s(item_id) for item_id in items]).delay()
        item_objects = items_task.get()
        total_cost = 0
        for item in item_objects:
            total_cost += int(item["price"])
        order["total_cost"] = total_cost
        return jsonify(order), 200
    else:
        return jsonify({"Error": "Order not found"}), 404


@app.post('/orders/checkout/<order_id>')
def checkout(order_id):
    task = orders.find_order.delay(order_id)
    order = task.get()
    if order:
        user_id = order["user_id"]
        total_cost = 0
        items = order["items"]
        print(items)
        items_task = group([stock.find_item.s(item_id) for item_id in items]).delay()
        item_objects = items_task.get()

        saga = Saga()

        for item in item_objects:
            total_cost += int(item["price"])

            # One saga step for each item to update
            saga.add_step(f"Decrease {item['_id']}", stock.remove_stock.s(item['_id'], 1), stock.add_stock.s(item['_id'], 1))

        # One saga step for payment
        saga.add_step(f"Payment user {user_id}: {total_cost}", payment.remove_credit.s(user_id, order_id, total_cost), 
                      payment.cancel_payment.s(user_id, order_id, total_cost))

        state = saga.run()

        if state == State.SUCCESS:
            return jsonify({"Success": True}), 200
        else:

            error = {}
            for step in saga.steps:
                error[step.name] = step.state.name
                print(f"Step {step.name}: {step.state}")
            
            return jsonify({"Error": error}), 400

    else:
        return jsonify({"Error": "Order not found"}), 404