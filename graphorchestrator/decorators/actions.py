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
    """
    Decorator to mark a function as a routing function.

    A routing function is responsible for deciding which node to execute next
    based on the current state of the graph. It receives the current state as
    input and should return the name of the next node as a string.

    Args:
        func: The function to be decorated. It should accept a State object and
            return a string (the name of the next node).

    Returns:
        A decorated function that performs the routing logic and type checking.

    """
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
    """
    Decorator to mark a function as a node action.

    A node action is a function that performs a specific task within a node
    in the graph. It receives the current state as input, modifies it, and
    returns the updated state.

    Args:
        func: The function to be decorated. It should accept a State object,
            modify it as needed, and return the updated State object.

    Returns:
        A decorated function that performs the node action logic and type checking.

    """

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
    """
    Decorator to mark a function as a tool method.

    A tool method is a function that represents a specific method within a
    tool. It receives the current state as input, performs a task using
    the tool, and returns the updated state. It is also a node action.

    Args:
        func: The function to be decorated. It should accept a State object,
            interact with the tool as needed, and return the updated State
            object.

    Returns:
        A decorated function that performs the tool method logic and type checking.

    """
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
    """
    Decorator to mark a function as an aggregator action.

    An aggregator action is a function that combines multiple states into a
    single state. This is useful when multiple nodes produce intermediate
    states that need to be merged.

    Args:
        func: The function to be decorated. It should accept a list of State
            objects, combine them into a single state, and return the
            resulting State object.

    Returns:
        A decorated function that performs the aggregator action logic and
        type checking.

    """
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
