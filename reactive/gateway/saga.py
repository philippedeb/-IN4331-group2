from enum import Enum

from celery import group
from inspect import iscoroutinefunction
import asyncio


class State(Enum):
    SUCCESS = 0
    COMPENSATED = 1
    FAILURE = 2
    CREATED = 3
    RUNNING = 4
    COMPENSATION_FAILURE = 5


class Step():
    """
    Saga step with action and compensation functions.
    These functions must return true if the execution was successful, false otherwise.
    """

    def __init__(self, name, action, compensation):
        self.name = name
        self.state = State.CREATED

        self.action = action
        self.compensation = compensation
        super().__init__()

    @staticmethod
    def create(name, action, compensation):
        if not callable(action) or not callable(compensation):
            return None
        return Step(name, action, compensation)


class Saga():
    """Saga class that runs a list of steps. If a step fails, the steps that succeded are reverted using the compensation function."""

    def __init__(self, logger, order_id):
        self.logger = logger
        self.order_id = order_id
        self.state = State.CREATED
        self.steps = []

        self.logger.log(self.order_id, "saga", self.state)


    def add_step(self, name, action, compensation):
        step = Step.create(name, action, compensation)
        if step is None:
            raise ValueError("Could not parse arguments into valid step type")
        self.steps.append(step)

    def run(self, *args, executor=None, **kwargs):
        """Run the saga"""
        self.state = State.RUNNING
        self.logger.update_log_state(self.order_id, self.state)
        
        stock_task = group([step.action for step in self.steps if "Decrease" in step.name]).delay()
        payment_task = group([step.action for step in self.steps if "Payment" in step.name]).delay()
        stock_results = stock_task.get()
        payment_results = payment_task.get()

        if all(stock_results) and all(payment_results):
            self.state = State.SUCCESS
            self.logger.update_log_state(self.order_id, self.state)
            for step in self.steps:
                step.state = State.SUCCESS
            return self.state
        else:
            self.state = State.FAILURE
            self.logger.update_log_state(self.order_id, self.state)
            for i,action in enumerate(stock_results):
                if not action:
                    self.steps[i].state = State.FAILURE
                else:
                    self.steps[i].state = State.SUCCESS
            
            compensation_task = group([step.compensation for step in self.steps if step.state == State.SUCCESS]).delay()

            if not payment_results[0]:
                self.steps[-1].state = State.FAILURE
            else:
                self.steps[-1].compensation.delay()
            return self.state

        
