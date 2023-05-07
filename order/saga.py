from enum import Enum

from inspect import iscoroutinefunction
import asyncio

class State(Enum):
    SUCCESS     = 0
    COMPENSATED = 1
    FAILURE     = 2
    CREATED     = 3
    RUNNING     = 4
    COMPENSATION_FAILURE = 5

class Step():
    """Saga step with action and compensation functions.
        These functions must return true if the execution was successful, false otherwise."""

    def __init__(self, name, action, compensation):
        self.name = name
        self.state = State.CREATED
        if not callable(action):
            raise ValueError("'func' argument must be callable")
        if not callable(compensation):
            raise ValueError("'compensation' argument must be callable")

        self.action = action
        self.compensation = compensation
        super().__init__()

    async def _run_func(self, func, *args, executor=None, **kwargs):
        if iscoroutinefunction(func):
            success = await func(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(executor, func, *args, **kwargs)
        return success
    
    async def run(self, *args, **kwargs):
        """Run the action function and set the state accordingly"""
        self.state = State.RUNNING
        success = await self._run_func(self.action, *args, **kwargs)
        if success:
            self.state = State.SUCCESS
        else:
            self.state = State.FAILURE
        return success
    
    async def compensate(self, *args, **kwargs):
        """Run the compensation function"""
        success = await self._run_func(self.compensation, *args, **kwargs)
        if success:
            self.state = State.COMPENSATED
        else:
            self.state = State.COMPENSATION_FAILURE
        return success

    @staticmethod
    def create(name, action, compensation):
        if not callable(action) or not callable(compensation):
            return None
        return Step(name, action, compensation)

class Saga():
    """Saga class that runs a list of steps. If a step fails, the steps that succeded are reverted using the compensation function"""
    def __init__(self):
        self.state = State.CREATED
        self.steps = []
    
    def add_step(self, name, action, compensation):
        step = Step.create(name, action, compensation)
        if step is None:
            raise ValueError("Could not parse arguments into valid step type")
        self.steps.append(step)

    async def run(self, *args, executor=None, **kwargs):       
        loop = asyncio.get_event_loop()
        
        # Run and wait for all steps
        futures = [
            step.run(*args, **kwargs)
            for step in self.steps
        ]
        await asyncio.gather(*futures)

        # If any step failed, compensate the ones that succeeded
        failure = any([step.state == State.FAILURE for step in self.steps])
        if failure:
            futures = [
                step.compensate(*args, **kwargs)
                for step in self.steps if step.state == State.SUCCESS
            ]
            await asyncio.gather(*futures)
        
        # Set overall saga state
        self.state = State.FAILURE if failure else State.SUCCESS