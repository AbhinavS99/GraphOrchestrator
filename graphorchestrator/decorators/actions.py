import asyncio
import logging
from functools import wraps
from typing import Callable, List

from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import (
    InvalidRoutingFunctionOutput,
    InvalidNodeActionOutput,
    InvalidToolMethodOutput,
    InvalidAggregatorActionError
)


def routing_function(func: Callable[[State], str]) -> Callable[[State], str]:
    @wraps(func)
    async def wrapper(state: State) -> str:
        show_state = getattr(func, "show_state", False)
        state_log = str(state) if show_state else f"<messages={len(state.messages)}>"
        logging.debug(f"Routing function '{func.__name__}' called with state={state_log}")
        result = await func(state) if asyncio.iscoroutinefunction(func) else func(state)
        if not isinstance(result, str):
            logging.error(f"Routing function '{func.__name__}' returned non-str: {result}")
            raise InvalidRoutingFunctionOutput(result)
        return result

    wrapper.is_routing_function = True
    return wrapper


def node_action(func: Callable[[State], State]) -> Callable[[State], State]:
    @wraps(func)
    async def wrapper(state: State) -> State:
        show_state = getattr(func, "show_state", False)
        state_log = str(state) if show_state else f"<messages={len(state.messages)}>"
        logging.debug(f"Node action '{func.__name__}' called with state={state_log}")
        result = await func(state) if asyncio.iscoroutinefunction(func) else func(state)
        if not isinstance(result, State):
            logging.error(f"Node action '{func.__name__}' returned non-State: {result}")
            raise InvalidNodeActionOutput(result)
        return result

    wrapper.is_node_action = True
    return wrapper


def tool_method(func: Callable[[State], State]) -> Callable[[State], State]:
    @wraps(func)
    async def wrapper(state: State) -> State:
        show_state = getattr(func, "show_state", False)
        state_log = str(state) if show_state else f"<messages={len(state.messages)}>"
        logging.debug(f"Tool method '{func.__name__}' called with state={state_log}")
        result = await func(state) if asyncio.iscoroutinefunction(func) else func(state)
        if not isinstance(result, State):
            logging.error(f"Tool method '{func.__name__}' returned non-State: {result}")
            raise InvalidToolMethodOutput(result)
        return result

    wrapper.is_node_action = True
    wrapper.is_tool_method = True
    return wrapper


def aggregator_action(func: Callable[[List[State]], State]) -> Callable[[List[State]], State]:
    @wraps(func)
    async def wrapper(states: List[State]) -> State:
        show_state = getattr(func, "show_state", False)
        state_log = str(states) if show_state else f"<batch_count={len(states)}>"
        logging.debug(f"Aggregator action '{func.__name__}' called with states={state_log}")
        result = await func(states) if asyncio.iscoroutinefunction(func) else func(states)
        if not isinstance(result, State):
            logging.error(f"Aggregator action '{func.__name__}' returned non-State: {result}")
            raise InvalidAggregatorActionError(result)
        return result

    wrapper.is_aggregator_action = True
    return wrapper
