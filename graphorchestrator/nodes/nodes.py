import asyncio
import logging
import httpx
from typing import Callable, List, Optional, Any, Dict, Awaitable
from graphorchestrator.decorators.actions import node_action

from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import (
    NodeActionNotDecoratedError,
    AggregatorActionNotDecorated,
    EmptyToolNodeDescriptionError,
    ToolMethodNotDecorated,
    InvalidAIActionOutput,
    InvalidNodeActionOutput,
)
from graphorchestrator.nodes.base import Node
from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class ProcessingNode(Node):
    """
    A node that processes the state.

    This node takes a function that operates on a State object, processes it,
    and returns a modified State object.
    """

    def __init__(self, node_id: str, func: Callable[[State], State]) -> None:
        super().__init__(node_id)
        self.func = func
        if not getattr(func, "is_node_action", False):
            raise NodeActionNotDecoratedError(func)

        GraphLogger.get().info(
            **wrap_constants(
                message="ProcessingNode created",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "ProcessingNode",
                    LC.ACTION: "node_created",
                    LC.CUSTOM: {"function": func.__name__},
                },
            )
        )

    async def execute(self, state: State) -> State:
        """
        Executes the processing logic of the node.

        Args:
            state (State): The input state for the node.

        Returns:
            State: The modified state after processing.
        """
        log = GraphLogger.get()

        log.info(
            **wrap_constants(
                message="ProcessingNode execution started",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "ProcessingNode",
                    LC.ACTION: "execute_start",
                    LC.INPUT_SIZE: len(state.messages),
                },
            )
        )

        result = (
            await self.func(state)
            if asyncio.iscoroutinefunction(self.func)
            else self.func(state)
        )

        log.info(
            **wrap_constants(
                message="ProcessingNode execution completed",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "ProcessingNode",
                    LC.ACTION: "execute_end",
                    LC.OUTPUT_SIZE: len(result.messages),
                },
            )
        )

        return result


class AggregatorNode(Node):
    """
    A node that aggregates multiple states into a single state.

    This node takes a list of State objects, aggregates them, and returns a
    new State object representing the aggregated result.
    """

    def __init__(
        self, node_id: str, aggregator_action: Callable[[List[State]], State]
    ) -> None:
        super().__init__(node_id)
        self.aggregator_action = aggregator_action
        if not getattr(aggregator_action, "is_aggregator_action", False):
            raise AggregatorActionNotDecorated(aggregator_action)

        GraphLogger.get().info(
            **wrap_constants(
                message="AggregatorNode created",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "AggregatorNode",
                    LC.ACTION: "node_created",
                    LC.CUSTOM: {"function": aggregator_action.__name__},
                },
            )
        )

    async def execute(self, states: List[State]) -> State:
        """
        Executes the aggregation logic of the node.

        Args:
            states (List[State]): The list of states to aggregate.

        Returns:
            State: The aggregated state.
        """
        log = GraphLogger.get()

        log.info(
            **wrap_constants(
                message="AggregatorNode execution started",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "AggregatorNode",
                    LC.ACTION: "execute_start",
                    LC.CUSTOM: {"input_batch_size": len(states)},
                },
            )
        )

        result = (
            await self.aggregator_action(states)
            if asyncio.iscoroutinefunction(self.aggregator_action)
            else self.aggregator_action(states)
        )

        log.info(
            **wrap_constants(
                message="AggregatorNode execution completed",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "AggregatorNode",
                    LC.ACTION: "execute_end",
                    LC.OUTPUT_SIZE: len(result.messages),
                },
            )
        )

        return result


class ToolNode(ProcessingNode):
    """
    A node that represents a tool.

    This node is a specialized ProcessingNode that wraps a tool method.
    """

    def __init__(
        self,
        node_id: str,
        description: Optional[str],
        tool_method: Callable[[State], State],
    ) -> None:
        if not getattr(tool_method, "is_tool_method", False):
            raise ToolMethodNotDecorated(tool_method)
        if not (description or (tool_method.__doc__ or "").strip()):
            raise EmptyToolNodeDescriptionError(tool_method)

        super().__init__(node_id, tool_method)
        self.description = description

        GraphLogger.get().info(
            **wrap_constants(
                message="ToolNode created",
                **{
                    LC.EVENT_TYPE: "tool",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "ToolNode",
                    LC.ACTION: "node_created",
                    LC.CUSTOM: {
                        "function": tool_method.__name__,
                        "has_description": bool(description),
                    },
                },
            )
        )

    async def execute(self, state: State) -> State:
        """
        Executes the tool method.

        Args:
            state (State): The input state for the node.

        Returns:
            State: The state after executing the tool method.
        """
        log = GraphLogger.get()

        log.info(
            **wrap_constants(
                message="ToolNode execution started",
                **{
                    LC.EVENT_TYPE: "tool",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "ToolNode",
                    LC.ACTION: "execute_start",
                    LC.INPUT_SIZE: len(state.messages),
                },
            )
        )

        result = (
            await self.func(state)
            if asyncio.iscoroutinefunction(self.func)
            else self.func(state)
        )

        log.info(
            **wrap_constants(
                message="ToolNode execution completed",
                **{
                    LC.EVENT_TYPE: "tool",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "ToolNode",
                    LC.ACTION: "execute_end",
                    LC.OUTPUT_SIZE: len(result.messages),
                },
            )
        )

        return result


class AINode(ProcessingNode):
    """
    A node that represents an AI model.

    This node wraps an AI model action.
    """

    def __init__(
        self,
        node_id: str,
        description: str,
        model_action: Callable[[State], State],
        response_format: Optional[str] = None,
        response_parser: Optional[Callable[[State], Any]] = None,
    ) -> None:
        super().__init__(node_id, model_action)
        self.description = description
        self.response_format = response_format
        self.response_parser = response_parser

        GraphLogger.get().info(
            **wrap_constants(
                message="AINode created",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "AINode",
                    LC.ACTION: "node_created",
                    LC.CUSTOM: {
                        "description": description,
                        "response_format": response_format,
                        "has_parser": bool(response_parser),
                    },
                },
            )
        )

    async def execute(self, state: State) -> State:
        """
        Executes the AI model action.

        Args:
            state (State): The input state for the node.

        Returns:
            State: The state after executing the model action.
        """
        log = GraphLogger.get()

        log.info(
            **wrap_constants(
                message="AINode execution started",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "AINode",
                    LC.ACTION: "execute_start",
                    LC.INPUT_SIZE: len(state.messages),
                },
            )
        )

        result = await self.func(state)

        if not isinstance(result, State):
            log.error(
                **wrap_constants(
                    message="AINode returned invalid output",
                    **{
                        LC.EVENT_TYPE: "node",
                        LC.NODE_ID: self.node_id,
                        LC.NODE_TYPE: "AINode",
                        LC.ACTION: "invalid_output",
                        LC.CUSTOM: {"result_type": str(type(result))},
                    },
                )
            )
            raise InvalidAIActionOutput(result)

        log.info(
            **wrap_constants(
                message="AINode execution completed",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "AINode",
                    LC.ACTION: "execute_end",
                    LC.OUTPUT_SIZE: len(result.messages),
                    LC.SUCCESS: True,
                },
            )
        )

        return result


class HumanInTheLoopNode(ProcessingNode):
    """
    A node that pauses execution for human input.
    """

    def __init__(
        self,
        node_id: str,
        interaction_handler: Callable[[State], Awaitable[State]],
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        if not getattr(interaction_handler, "is_node_action", False):
            interaction_handler = node_action(interaction_handler)

        self.metadata = metadata or {}

        GraphLogger.get().info(
            **wrap_constants(
                message="Human-in-the-loop node created",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: node_id,
                    LC.NODE_TYPE: "HumanInTheLoopNode",
                    LC.ACTION: "node_created",
                    LC.CUSTOM: {"metadata_keys": list(self.metadata.keys())},
                },
            )
        )

        super().__init__(node_id, interaction_handler)

    async def execute(self, state: State) -> State:
        """
        Executes the human-in-the-loop interaction.
        """
        log = GraphLogger.get()

        log.info(
            **wrap_constants(
                message="HumanInTheLoopNode execution started",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "HumanInTheLoopNode",
                    LC.ACTION: "execute_start",
                    LC.INPUT_SIZE: len(state.messages),
                },
            )
        )

        result = await self.func(state)

        if not isinstance(result, State):
            log.error(
                **wrap_constants(
                    message="Invalid output from human-in-the-loop handler",
                    **{
                        LC.EVENT_TYPE: "node",
                        LC.NODE_ID: self.node_id,
                        LC.NODE_TYPE: "HumanInTheLoopNode",
                        LC.ACTION: "invalid_output",
                        LC.CUSTOM: {"result_type": str(type(result))},
                    },
                )
            )
            raise InvalidNodeActionOutput(result)

        log.info(
            **wrap_constants(
                message="HumanInTheLoopNode execution completed",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: self.node_id,
                    LC.NODE_TYPE: "HumanInTheLoopNode",
                    LC.ACTION: "execute_end",
                    LC.OUTPUT_SIZE: len(result.messages),
                    LC.SUCCESS: True,
                },
            )
        )

        return result


class ToolSetNode(ProcessingNode):
    """
    A ProcessingNode that invokes a remote ToolSetServer endpoint as an HTTP call.

    Each execution:
    1. Sends the current State.messages as JSON to `{base_url}/tools/{tool_name}`.
    2. Parses the JSON response into a new State.
    """

    httpx = httpx

    def __init__(self, node_id: str, base_url: str, tool_name: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.tool_name = tool_name
        action = self._make_tool_action()

        GraphLogger.get().info(
            **wrap_constants(
                message="ToolSetNode initialized",
                **{
                    LC.EVENT_TYPE: "tool",
                    LC.NODE_ID: node_id,
                    LC.NODE_TYPE: "ToolSetNode",
                    LC.ACTION: "node_created",
                    LC.CUSTOM: {"tool_name": self.tool_name, "base_url": self.base_url},
                },
            )
        )

        super().__init__(node_id, action)

    def _make_tool_action(self) -> Callable[[State], State]:
        """
        Constructs the @node_action-wrapped coroutine that performs the HTTP call.
        """
        url = f"{self.base_url}/tools/{self.tool_name}"

        @node_action
        async def _action(state: State) -> State:
            log = GraphLogger.get()

            log.info(
                **wrap_constants(
                    message="ToolSetNode HTTP request started",
                    **{
                        LC.EVENT_TYPE: "tool",
                        LC.NODE_ID: self.node_id,
                        LC.NODE_TYPE: "ToolSetNode",
                        LC.ACTION: "tool_http_start",
                        LC.INPUT_SIZE: len(state.messages),
                        LC.CUSTOM: {"url": url},
                    },
                )
            )

            payload = {"messages": state.messages}
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
                new_state = State(messages=data.get("messages", []))

                log.info(
                    **wrap_constants(
                        message="ToolSetNode HTTP call succeeded",
                        **{
                            LC.EVENT_TYPE: "tool",
                            LC.NODE_ID: self.node_id,
                            LC.NODE_TYPE: "ToolSetNode",
                            LC.ACTION: "tool_http_success",
                            LC.OUTPUT_SIZE: len(new_state.messages),
                            LC.SUCCESS: True,
                            LC.CUSTOM: {"url": url, "status_code": resp.status_code},
                        },
                    )
                )

                return new_state

        return _action
