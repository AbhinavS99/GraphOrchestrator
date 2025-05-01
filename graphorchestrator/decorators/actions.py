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
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


def routing_function(func: Callable[[State], str]) -> Callable[[State], str]:
    @wraps(func)
    async def wrapper(state: State) -> str:
        log = GraphLogger.get()
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

    wrapper.is_routing_function = True
    return wrapper


def node_action(func: Callable[[State], State]) -> Callable[[State], State]:
    @wraps(func)
    async def wrapper(state: State) -> State:
        log = GraphLogger.get()
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

    wrapper.is_node_action = True
    return wrapper


def tool_method(func: Callable[[State], State]) -> Callable[[State], State]:
    @wraps(func)
    async def wrapper(state: State) -> State:
        log = GraphLogger.get()
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

    wrapper.is_node_action = True
    wrapper.is_tool_method = True
    return wrapper


def aggregator_action(
    func: Callable[[List[State]], State],
) -> Callable[[List[State]], State]:
    @wraps(func)
    async def wrapper(states: List[State]) -> State:
        log = GraphLogger.get()
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

        result = (
            await func(states) if asyncio.iscoroutinefunction(func) else func(states)
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

    wrapper.is_aggregator_action = True
    return wrapper
