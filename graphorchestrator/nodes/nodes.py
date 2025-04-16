import asyncio
import logging
from typing import Callable, List, Optional, Any

from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import (
    NodeActionNotDecoratedError,
    AggregatorActionNotDecorated,
    EmptyToolNodeDescriptionError,
    ToolMethodNotDecorated,
    InvalidAIActionOutput
)
from graphorchestrator.nodes.base import Node

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
        logging.info(f"node=processing event=created node_id={self.node_id} func={func.__name__}")

    async def execute(self, state: State) -> State:
        """
        Executes the processing logic of the node.

        Args:
            state (State): The input state for the node.

        Returns:
            State: The modified state after processing.
        """
        logging.debug(f"node=processing event=execute_start node_id={self.node_id} input_size={len(state.messages)}")
        result = await self.func(state) if asyncio.iscoroutinefunction(self.func) else self.func(state)
        logging.debug(f"node=processing event=execute_end node_id={self.node_id} result_size={len(result.messages)}")
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
    def __init__(self, node_id: str, aggregator_action: Callable[[List[State]], State]) -> None:
        super().__init__(node_id)
        self.aggregator_action = aggregator_action
        if not getattr(aggregator_action, "is_aggregator_action", False):
            raise AggregatorActionNotDecorated(aggregator_action)
        logging.info(f"node=aggregator event=created node_id={self.node_id} func={aggregator_action.__name__}")

    async def execute(self, states: List[State]) -> State:
        """
        Executes the aggregation logic of the node.

        Args:
            states (List[State]): The list of states to aggregate.

        Returns:
            State: The aggregated state.
        """
        logging.debug(f"node=aggregator event=execute_start node_id={self.node_id} input_batch={len(states)}")
        result = await self.aggregator_action(states) if asyncio.iscoroutinefunction(self.aggregator_action) else self.aggregator_action(states)
        logging.debug(f"node=aggregator event=execute_end node_id={self.node_id} result_size={len(result.messages)}")
        return result

class ToolNode(ProcessingNode):
    """
    A node that represents a tool.

    This node is a specialized ProcessingNode that wraps a tool method.
    Args:
      node_id: node id
      tool_method: tool function to be executed
    """
    def __init__(self, node_id: str,  description: Optional[str], tool_method: Callable[[State], State]) -> None:
        if not getattr(tool_method, "is_tool_method", False):
            raise ToolMethodNotDecorated(tool_method)
        if not (description or (tool_method.__doc__ or "").strip()):
            raise EmptyToolNodeDescriptionError(tool_method)
        super().__init__(node_id, tool_method)
        self.description = description
        logging.info(f"node=tool event=created node_id={self.node_id} func={tool_method.__name__} desc={'yes' if description else 'docstring'}")

    async def execute(self, state: State) -> State:
        """
        Executes the tool method.

        Args:
            state (State): The input state for the node.

        Returns:
            State: The state after executing the tool method.
        """
        logging.debug(f"node=tool event=execute_start node_id={self.node_id} input_size={len(state.messages)}")
        result = await self.func(state) if asyncio.iscoroutinefunction(self.func) else self.func(state)
        logging.debug(f"node=tool event=execute_end node_id={self.node_id} result_size={len(result.messages)}")
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
    def __init__(self, node_id: str, description: str, model_action: Callable[[State], State], response_format: Optional[str] = None, response_parser: Optional[Callable[[State], Any]] = None) -> None:
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
        logging.debug(f"node=ai event=execute_start node_id={self.node_id} input_size={len(state.messages)}")
        result = await self.func(state)
        if not isinstance(result, State):
            logging.error(f"node=ai event=invalid_output node_id={self.node_id} result_type={type(result)}")
            raise InvalidAIActionOutput(result)
        logging.debug(f"node=ai event=execute_end node_id={self.node_id} result_size={len(result.messages)}")
        return result
