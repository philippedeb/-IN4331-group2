from fastapi import FastAPI, status, HTTPException

import payment.tasks as payment
import stock.tasks as stock
import order.tasks as order

app = FastAPI()


@app.get('/', status_code=status.HTTP_200_OK)
def index():
    return "Health check"

@app.post('/payment/create_user', status_code=status.HTTP_200_OK)
def create_user():
    task = payment.create_user.delay()
    user = task.get()
    if user and not task.failed():
        return user
    else:
        raise HTTPException(status_code=500, detail="Error creating user")


@app.get('/payment/find_user/{user_id}', status_code=status.HTTP_200_OK)
def find_user(user_id: str):
    task = payment.find_user.delay(user_id)
    user = task.get()
    if user and not task.failed():
        return user
    else:
        raise HTTPException(status_code=404, detail="User not found")


@app.post('/payment/add_funds/{user_id}/{amount}', status_code=status.HTTP_200_OK)
def add_credit(user_id: str, amount: int):
    task = payment.add_credit.delay(user_id, amount)
    result = task.get()
    if result and not task.failed():
        return {"Success": True}
    else:
        raise HTTPException(status_code=404, detail="User not found")


@app.post('/payment/pay/{user_id}/{order_id}/{amount}', status_code=status.HTTP_200_OK)
def remove_credit(user_id: str, order_id: str, amount: int):
    task = payment.remove_credit.delay(user_id, amount)
    result = task.get()
    if result and not task.failed():
        return {"Success": True}
    else:
        raise HTTPException(status_code=400, detail="Not enough credit or user not found")


@app.post('/payment/cancel/{user_id}/{order_id}/{amount}', status_code=status.HTTP_200_OK)
def cancel_payment(user_id: str, order_id: str, amount: int):
    task = payment.cancel_payment.delay(user_id, amount)
    result = task.get()
    if result and not task.failed():
        return {"Success": True}
    else:
        raise HTTPException(status_code=404, detail="Payment not found")


@app.post('/payment/status/{user_id}/{order_id}', status_code=status.HTTP_200_OK)
def payment_status(user_id: str, order_id: str):
    task = payment.payment_status.delay(user_id, order_id)
    result = task.get()
    if result and not task.failed():
        return result
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.post('/stock/item/create/{price}', status_code=status.HTTP_200_OK)
def create_item(price: int):
    task = stock.create_item.delay(price)
    item = task.get()
    if item and not task.failed():
        return item
    else:
        raise HTTPException(status_code=500, detail="Error creating item")

@app.get('/stock/find/{item_id}', status_code=status.HTTP_200_OK)
def find_item(item_id: str):
    task = stock.find_item.delay(item_id)
    item = task.get()
    if item and not task.failed():
        return item
    else:
        raise HTTPException(status_code=404, detail="Item not found")


@app.post('/stock/add/{item_id}/{amount}', status_code=status.HTTP_200_OK)
def add_stock(item_id: str, amount: int):
    task = stock.add_stock.delay(item_id, amount)
    result = task.get()
    if result and not task.failed():
        return {"Success": True}
    else:
        raise HTTPException(status_code=404, detail="Item not found")


@app.post('/stock/subtract/{item_id}/{amount}', status_code=status.HTTP_200_OK)
def remove_stock(item_id: str, amount: int):
    task = stock.remove_stock.delay(item_id, amount)
    result = task.get()
    if result and not task.failed():
        return {"Success": True}
    else:
        raise HTTPException(status_code=400, detail="Not enough stock or item not found")
    
@app.post('/orders/create/{user_id}', status_code=status.HTTP_200_OK)
def create_order(user_id):
    task = order.create_order.delay(user_id)
    order = task.get()
    if order and not task.failed():
        return order
    else:
        raise HTTPException(status_code=500, detail="Error creating order")


@app.delete('/orders/remove/{order_id}', status_code=status.HTTP_200_OK)
def remove_order(order_id):
    task = order.remove_order.delay(order_id)
    result = task.get()
    if result and not task.failed():
        return {"success": True}
    else:
        raise HTTPException(status_code=404, detail="Order not found")

@app.post('/orders/addItem/{order_id}/{item_id}', status_code=status.HTTP_200_OK)
def add_item(order_id, item_id):
    task = order.add_item.delay(order_id, item_id)
    result = task.get()
    if result and not task.failed():
        return {"success": True}
    else:
        raise HTTPException(status_code=404, detail="Order not found")


@app.delete('/orders/removeItem/{order_id}/{item_id}', status_code=status.HTTP_200_OK)
def remove_item(order_id, item_id):
    task = order.remove_item.delay(order_id, item_id)
    result = task.get()
    if result and not task.failed():
        return {"success": True}
    else:
        raise HTTPException(status_code=404, detail="Order not found")

@app.get('/orders/find/{order_id}', status_code=status.HTTP_200_OK)
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


@app.post('/orders/checkout/{order_id}', status_code=status.HTTP_200_OK)
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