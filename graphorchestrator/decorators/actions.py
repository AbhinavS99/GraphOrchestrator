import asyncio
from functools import wraps
from typing import Callable, List

from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import (
    InvalidRoutingFunctionOutput,
    InvalidNodeActionOutput,
    InvalidToolMethodOutput,
    InvalidAggregatorActionError,
)
from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import (
    wrap_constants,
)  # Function to wrap constants for logging
from graphorchestrator.core.log_constants import LogConstants as LC


# Decorator for routing functions
def routing_function(func: Callable[[State], str]) -> Callable[[State], str]:
    """
    Decorator for functions that route the flow of the graph.
    These functions must take a State and return a string.
    """

    @wraps(func)
    async def wrapper(state: State) -> str:
        # Get the logger
        log = GraphLogger.get()
        # Check if the state should be shown in the logs.
        # This flag can be set in the function itself.
        # Otherwise only number of messages are shown
        show_state = getattr(func, "show_state", False)
        state_log = str(state) if show_state else f"<messages={len(state.messages)}>"

        log.debug(
            **wrap_constants(
                message="Routing function invoked",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.ACTION: "routing_function_invoked",
                    LC.CUSTOM: {"function": func.__name__, "state": state_log},
                },
            )
        )
        # Invoke the function based on its type.
        # if its a coroutine invoke it with await.
        # otherwise invoke directly.
        # Save the result.
        result = await func(state) if asyncio.iscoroutinefunction(func) else func(state)
        if not isinstance(result, str):
            log.error(
                **wrap_constants(
                    message="Routing function returned non-string",
                    **{
                        LC.EVENT_TYPE: "node",
                        LC.ACTION: "routing_invalid_output",
                        LC.CUSTOM: {
                            "function": func.__name__,
                            "returned_type": str(type(result)),
                            "value": str(result)[:100],
                        },
                    },
                )
            )
            raise InvalidRoutingFunctionOutput(result)
        return result

    # Add a flag to identify this function as a routing function
    wrapper.is_routing_function = True
    return wrapper


# Decorator for node actions
def node_action(func: Callable[[State], State]) -> Callable[[State], State]:
    """
    Decorator for functions that are node actions.
    These functions must take a State and return a State.
    """

    @wraps(func)
    async def wrapper(state: State) -> State:
        # Get the logger
        log = GraphLogger.get()
        # Check if the state should be shown in the logs.
        # This flag can be set in the function itself.
        show_state = getattr(func, "show_state", False)
        state_log = str(state) if show_state else f"<messages={len(state.messages)}>"

        log.debug(
            **wrap_constants(
                message="Node action invoked",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.ACTION: "node_action_invoked",
                    LC.CUSTOM: {"function": func.__name__, "state": state_log},
                },
            )
        )
        # Invoke the function based on its type.
        # if its a coroutine invoke it with await.
        # otherwise invoke directly.
        # Save the result.
        result = await func(state) if asyncio.iscoroutinefunction(func) else func(state)
        if not isinstance(result, State):
            log.error(
                **wrap_constants(
                    message="Node action returned invalid output",
                    **{
                        LC.EVENT_TYPE: "node",
                        LC.ACTION: "node_invalid_output",
                        LC.CUSTOM: {
                            "function": func.__name__,
                            "returned_type": str(type(result)),
                            "value": str(result)[:100],
                        },
                    },
                )
            )
            raise InvalidNodeActionOutput(result)
        return result

    # Add a flag to identify this function as a node action
    wrapper.is_node_action = True
    return wrapper


# Decorator for tool methods
def tool_method(func: Callable[[State], State]) -> Callable[[State], State]:
    """
    Decorator for functions that are tool methods.
    These functions must take a State and return a State.
    """

    @wraps(func)
    async def wrapper(state: State) -> State:
        # Get the logger
        log = GraphLogger.get()
        # Check if the state should be shown in the logs.
        # This flag can be set in the function itself.
        show_state = getattr(func, "show_state", False)
        state_log = str(state) if show_state else f"<messages={len(state.messages)}>"

        log.debug(
            **wrap_constants(
                message="Tool method invoked",
                **{
                    LC.EVENT_TYPE: "tool",
                    LC.ACTION: "tool_method_invoked",
                    LC.CUSTOM: {"function": func.__name__, "state": state_log},
                },
            )
        )
        # Invoke the function based on its type.
        # if its a coroutine invoke it with await.
        # otherwise invoke directly.
        # Save the result.
        result = await func(state) if asyncio.iscoroutinefunction(func) else func(state)
        if not isinstance(result, State):
            log.error(
                **wrap_constants(
                    message="Tool method returned invalid output",
                    **{
                        LC.EVENT_TYPE: "tool",
                        LC.ACTION: "tool_invalid_output",
                        LC.CUSTOM: {
                            "function": func.__name__,
                            "returned_type": str(type(result)),
                            "value": str(result)[:100],
                        },
                    },
                )
            )
            raise InvalidToolMethodOutput(result)
        return result

    # Add flags to identify this function as a node action and a tool method
    wrapper.is_node_action = True
    wrapper.is_tool_method = True
    return wrapper


# Decorator for aggregator actions
def aggregator_action(
    func: Callable[[List[State]], State],
) -> Callable[[List[State]], State]:
    """
    Decorator for functions that are aggregator actions.
    These functions must take a list of States and return a State.
    """

    @wraps(func)
    async def wrapper(states: List[State]) -> State:
        # Get the logger
        log = GraphLogger.get()
        # Check if the state should be shown in the logs.
        show_state = getattr(func, "show_state", False)
        state_log = str(states) if show_state else f"<batch_count={len(states)}>"

        log.debug(
            **wrap_constants(
                message="Aggregator action invoked",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.ACTION: "aggregator_invoked",
                    LC.CUSTOM: {"function": func.__name__, "batch_summary": state_log},
                },
            )
        )
        # Invoke the function based on its type.
        # if its a coroutine invoke it with await.
        # otherwise invoke directly.
        # Save the result.
        result = (
            await func(states) if asyncio.iscoroutinefunction(func) else func(states)  # type: ignore
        )
        if not isinstance(result, State):
            log.error(
                **wrap_constants(
                    message="Aggregator returned invalid output",
                    **{
                        LC.EVENT_TYPE: "node",
                        LC.ACTION: "aggregator_invalid_output",
                        LC.CUSTOM: {
                            "function": func.__name__,
                            "returned_type": str(type(result)),
                            "value": str(result)[:100],
                        },
                    },
                )
            )
            raise InvalidAggregatorActionError(result)
        return result

    # Add a flag to identify this function as an aggregator action
    wrapper.is_aggregator_action = True
    return wrapper
