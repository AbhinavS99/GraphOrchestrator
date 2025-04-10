from abc import ABC, abstractmethod
from collections import abc
from typing import Any

from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import InvalidAIActionOutput

class AIActionBase(ABC):
    def __init__(self, config: dict) -> None:
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
            self._model_built = True
        """
        pass

    @abstractmethod
    async def process_state(self, state: State) -> State:
        """
        Main logic to process a state using the AI model.
        """
        pass

    async def __call__(self, state: State) -> State:
        if not self._model_built:
            self.build_model()

        result_or_coro = self.process_state(state)
        result = await result_or_coro if isinstance(result_or_coro, abc.Awaitable) else result_or_coro

        if not isinstance(result, State):
            raise InvalidAIActionOutput(result)

        return result
