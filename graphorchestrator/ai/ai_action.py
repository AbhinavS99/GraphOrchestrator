from abc import ABC, abstractmethod
from collections import abc
from typing import Any

from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import InvalidAIActionOutput


class AIActionBase(ABC):
    """
    Abstract base class for defining AI actions within the graph orchestration framework.

    AI actions are specialized nodes capable of processing and modifying the state
    of the graph using an underlying AI model.
    """

    def __init__(self, config: dict) -> None:
        """
        Initializes an AIActionBase instance.

        Args:
            config (dict): Configuration parameters for the AI model.
        """
        self.config: dict = config
        self._model_built = False
        self.model: Any = None
        self.is_node_action = True
        self.__name__ = self.__class__.__name__


    @abstractmethod
    def build_model(self):
        """
        Build and configure the model.
        Subclasses must set:
            self.model = <constructed model>
            self._model_built = True.
        
        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def process_state(self, state: State) -> State:
        """
        Main logic to process a state using the AI model.
        This method must be implemented by subclasses to define the specific
        AI processing logic.

        Args:
            state (State): The current state of the graph.

        Returns:
            State: The modified state after processing.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError

    async def __call__(self, state: State) -> State:
        """
        Invokes the AI action's processing logic.

        Args:
            state (State): The current state of the graph.

        Returns:
            State: The modified state after processing.
        """
        if not self._model_built:
            self.build_model()

        result_or_coro = self.process_state(state)
        result = await result_or_coro if isinstance(result_or_coro, abc.Awaitable) else result_or_coro

        if not isinstance(result, State):
            raise InvalidAIActionOutput(result)

        return result
