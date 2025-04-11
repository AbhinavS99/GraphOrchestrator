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
    def __init__(self, node_id: str, func: Callable[[State], State]) -> None:
        super().__init__(node_id)
        self.func = func
        if not getattr(func, "is_node_action", False):
            raise NodeActionNotDecoratedError(func)
        logging.info(f"node=processing event=created node_id={self.node_id} func={func.__name__}")

    async def execute(self, state: State) -> State:
        logging.debug(f"node=processing event=execute_start node_id={self.node_id} input_size={len(state.messages)}")
        result = await self.func(state) if asyncio.iscoroutinefunction(self.func) else self.func(state)
        logging.debug(f"node=processing event=execute_end node_id={self.node_id} result_size={len(result.messages)}")
        return result

class AggregatorNode(Node):
    def __init__(self, node_id: str, aggregator_action: Callable[[List[State]], State]) -> None:
        super().__init__(node_id)
        self.aggregator_action = aggregator_action
        if not getattr(aggregator_action, "is_aggregator_action", False):
            raise AggregatorActionNotDecorated(aggregator_action)
        logging.info(f"node=aggregator event=created node_id={self.node_id} func={aggregator_action.__name__}")

    async def execute(self, states: List[State]) -> State:
        logging.debug(f"node=aggregator event=execute_start node_id={self.node_id} input_batch={len(states)}")
        result = await self.aggregator_action(states) if asyncio.iscoroutinefunction(self.aggregator_action) else self.aggregator_action(states)
        logging.debug(f"node=aggregator event=execute_end node_id={self.node_id} result_size={len(result.messages)}")
        return result

class ToolNode(ProcessingNode):
    def __init__(self, node_id: str,  description: Optional[str], tool_method: Callable[[State], State]) -> None:
        if not getattr(tool_method, "is_tool_method", False):
            raise ToolMethodNotDecorated(tool_method)
        if not (description or (tool_method.__doc__ or "").strip()):
            raise EmptyToolNodeDescriptionError(tool_method)
        super().__init__(node_id, tool_method)
        self.description = description
        logging.info(f"node=tool event=created node_id={self.node_id} func={tool_method.__name__} desc={'yes' if description else 'docstring'}")

    async def execute(self, state: State) -> State:
        logging.debug(f"node=tool event=execute_start node_id={self.node_id} input_size={len(state.messages)}")
        result = await self.func(state) if asyncio.iscoroutinefunction(self.func) else self.func(state)
        logging.debug(f"node=tool event=execute_end node_id={self.node_id} result_size={len(result.messages)}")
        return result

class AINode(ProcessingNode):
    def __init__(self, node_id: str, description: str, model_action: Callable[[State], State], response_format: Optional[str] = None, response_parser: Optional[Callable[[State], Any]] = None) -> None:
        super().__init__(node_id, model_action)
        self.description = description
        self.response_format = response_format
        self.response_parser = response_parser
        logging.info(f"node=ai event=created node_id={self.node_id} desc={description}")

    async def execute(self, state: State) -> State:
        logging.debug(f"node=ai event=execute_start node_id={self.node_id} input_size={len(state.messages)}")
        result = await self.func(state)
        if not isinstance(result, State):
            logging.error(f"node=ai event=invalid_output node_id={self.node_id} result_type={type(result)}")
            raise InvalidAIActionOutput(result)
        logging.debug(f"node=ai event=execute_end node_id={self.node_id} result_size={len(result.messages)}")
        return result
