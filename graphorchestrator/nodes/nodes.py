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
from graphorchestrator.core.retry import RetryPolicy


class ProcessingNode(Node):
    """
    A node that processes the state.

    This node takes a function that operates on a State object, processes it,
    and returns a modified State object.

    Args:
        node_id (str): The unique identifier for the processing node.
        func (Callable[[State], State]): The function that processes the State.
    """

    def __init__(self, node_id: str, func: Callable[[State], State]) -> None:
        super().__init__(node_id)
        self.func = func
        if not getattr(func, "is_node_action", False):
            raise NodeActionNotDecoratedError(func)
        logging.info(
            f"node=processing event=created node_id={self.node_id} func={func.__name__}"
        )

    async def execute(self, state: State) -> State:
        """
        Executes the processing logic of the node.

        Args:
            state (State): The input state for the node.

        Returns:
            State: The modified state after processing.
        """
        logging.debug(
            f"node=processing event=execute_start node_id={self.node_id} input_size={len(state.messages)}"
        )
        result = (
            await self.func(state)
            if asyncio.iscoroutinefunction(self.func)
            else self.func(state)
        )
        logging.debug(
            f"node=processing event=execute_end node_id={self.node_id} result_size={len(result.messages)}"
        )
        return result


class AggregatorNode(Node):
    """
    A node that aggregates multiple states into a single state.

    This node takes a list of State objects, aggregates them, and returns a
    new State object representing the aggregated result.

    Args:
        node_id (str): The unique identifier for the aggregator node.
        aggregator_action (Callable[[List[State]], State]): The aggregation function.
    """

    def __init__(
        self, node_id: str, aggregator_action: Callable[[List[State]], State]
    ) -> None:
        super().__init__(node_id)
        self.aggregator_action = aggregator_action
        if not getattr(aggregator_action, "is_aggregator_action", False):
            raise AggregatorActionNotDecorated(aggregator_action)
        logging.info(
            f"node=aggregator event=created node_id={self.node_id} func={aggregator_action.__name__}"
        )

    async def execute(self, states: List[State]) -> State:
        """
        Executes the aggregation logic of the node.

        Args:
            states (List[State]): The list of states to aggregate.

        Returns:
            State: The aggregated state.
        """
        logging.debug(
            f"node=aggregator event=execute_start node_id={self.node_id} input_batch={len(states)}"
        )
        result = (
            await self.aggregator_action(states)
            if asyncio.iscoroutinefunction(self.aggregator_action)
            else self.aggregator_action(states)
        )
        logging.debug(
            f"node=aggregator event=execute_end node_id={self.node_id} result_size={len(result.messages)}"
        )
        return result


class ToolNode(ProcessingNode):
    """
    A node that represents a tool.

    This node is a specialized ProcessingNode that wraps a tool method.
    Args:
      node_id: node id
      tool_method: tool function to be executed
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
        logging.info(
            f"node=tool event=created node_id={self.node_id} func={tool_method.__name__} desc={'yes' if description else 'docstring'}"
        )

    async def execute(self, state: State) -> State:
        """
        Executes the tool method.

        Args:
            state (State): The input state for the node.

        Returns:
            State: The state after executing the tool method.
        """
        logging.debug(
            f"node=tool event=execute_start node_id={self.node_id} input_size={len(state.messages)}"
        )
        result = (
            await self.func(state)
            if asyncio.iscoroutinefunction(self.func)
            else self.func(state)
        )
        logging.debug(
            f"node=tool event=execute_end node_id={self.node_id} result_size={len(result.messages)}"
        )
        return result


class AINode(ProcessingNode):
    """
    A node that represents an AI model.

    This node wraps an AI model action.

    Args:
        node_id (str): The unique identifier for the AI node.
        description (str): A description of the AI model.
        model_action (Callable[[State], State]): The AI model action function.
        response_format (Optional[str]): The expected response format.
        response_parser (Optional[Callable[[State], Any]]): A parser for the response.

    Raises:
        InvalidAIActionOutput: If the output of the model action is not a State.
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
        logging.info(f"node=ai event=created node_id={self.node_id} desc={description}")

    async def execute(self, state: State) -> State:
        """
        Executes the AI model action.

        Args:
            state (State): The input state for the node.

        Returns:
            State: The state after executing the model action.

        """
        logging.debug(
            f"node=ai event=execute_start node_id={self.node_id} input_size={len(state.messages)}"
        )
        result = await self.func(state)
        if not isinstance(result, State):
            logging.error(
                f"node=ai event=invalid_output node_id={self.node_id} result_type={type(result)}"
            )
            raise InvalidAIActionOutput(result)
        logging.debug(
            f"node=ai event=execute_end node_id={self.node_id} result_size={len(result.messages)}"
        )
        return result


class HumanInTheLoopNode(ProcessingNode):
    """
    A node that pauses execution for human input.

    This node allows a human to manually inspect and modify the state before execution proceeds.
    The interaction logic is user-defined and can involve CLI prompts, UIs, webhooks, etc.

    Args:
        node_id (str): The unique identifier for the human-in-the-loop node.
        interaction_handler (Callable[[State], State]): The async function that handles human interaction.
        metadata (Optional[Dict[str, str]]): Optional metadata describing the human input or prompt.

    Raises:
        InvalidNodeActionOutput: If the interaction handler returns an invalid state.
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
        logging.info(
            f"node=human event=created node_id={node_id} metadata_keys={list(self.metadata.keys())}"
        )
        super().__init__(node_id, interaction_handler)

    async def execute(self, state: State) -> State:
        """
        Executes the human-in-the-loop interaction.

        Args:
            state (State): The input state awaiting human intervention.

        Returns:
            State: The state after human interaction.

        Raises:
            InvalidNodeActionOutput: If the interaction handler returns invalid output.
        """
        logging.debug(
            f"node=human event=execute_start node_id={self.node_id} input_size={len(state.messages)}"
        )
        result = await self.func(state)
        if not isinstance(result, State):
            logging.error(
                f"node=human event=invalid_output node_id={self.node_id} result_type={type(result)}"
            )
            raise InvalidNodeActionOutput(result)
        logging.debug(
            f"node=human event=execute_end node_id={self.node_id} result_size={len(result.messages)}"
        )
        return result


class ToolSetNode(ProcessingNode):
    """
    A ProcessingNode that invokes a remote ToolSetServer endpoint as an HTTP call.

    Each execution:
    1. Sends the current State.messages as JSON to `{base_url}/tools/{tool_name}`.
    2. Parses the JSON response into a new State.

    Args:
        node_id (str): Unique identifier for this node.
        base_url (str): Base URL of the ToolSetServer (trailing slash is stripped).
        tool_name (str): Name of the tool (path segment under `/tools`).
    """

    httpx = httpx

    def __init__(self, node_id: str, base_url: str, tool_name: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.tool_name = tool_name
        action = self._make_tool_action()
        super().__init__(node_id, action)

    def _make_tool_action(self) -> Callable[[State], State]:
        """
        Constructs the @node_action-wrapped coroutine that performs the HTTP call.
        """
        url = f"{self.base_url}/tools/{self.tool_name}"

        @node_action
        async def _action(state: State) -> State:
            logging.info(f"node=toolset event=start node_id={self.node_id} url={url}")
            payload = {"messages": state.messages}
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
                new_state = State(messages=data.get("messages", []))
                logging.info(
                    f"node=toolset event=success node_id={self.node_id} messages={len(new_state.messages)}"
                )
                return new_state

        return _action
