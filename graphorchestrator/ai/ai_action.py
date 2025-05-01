from abc import ABC, abstractmethod
from collections import abc
from typing import Any

from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import InvalidAIActionOutput

from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


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

        log = GraphLogger.get()
        node_label = self.__name__

        log.info(
            **wrap_constants(
                message="AIActionBase initialized",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.ACTION: "node_created",
                    LC.NODE_ID: node_label,
                    LC.NODE_TYPE: "AINode",
                    LC.CUSTOM: {"config": self.config},  # Full config included here
                }
            )
        )

    @abstractmethod
    def build_model(self):
        """
        Build and configure the model.
        Subclasses must set:
            self.model = <constructed model>
            self._model_built = True.
        """
        raise NotImplementedError

    @abstractmethod
    async def process_state(self, state: State) -> State:
        """
        Main logic to process a state using the AI model.
        """
        raise NotImplementedError

    async def __call__(self, state: State) -> State:
        """
        Invokes the AI action's processing logic.
        """
        log = GraphLogger.get()
        node_label = getattr(self, "__name__", self.__class__.__name__)

        if not self._model_built:
            self.build_model()

            log.info(
                **wrap_constants(
                    message="AI model built",
                    **{
                        LC.EVENT_TYPE: "node",
                        LC.NODE_ID: node_label,
                        LC.NODE_TYPE: "AINode",
                        LC.ACTION: "build_model",
                        LC.CUSTOM: {"config": self.config},
                    }
                )
            )

        log.info(
            **wrap_constants(
                message="AI node execution started",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: node_label,
                    LC.NODE_TYPE: "AINode",
                    LC.ACTION: "execute_start",
                    LC.INPUT_SIZE: len(state.messages),
                }
            )
        )

        result_or_coro = self.process_state(state)
        result = (
            await result_or_coro
            if isinstance(result_or_coro, abc.Awaitable)
            else result_or_coro
        )

        if not isinstance(result, State):
            log.error(
                **wrap_constants(
                    message="AI action returned non-State object",
                    **{
                        LC.EVENT_TYPE: "node",
                        LC.NODE_ID: node_label,
                        LC.NODE_TYPE: "AINode",
                        LC.ACTION: "invalid_output",
                        LC.CUSTOM: {"actual_type": str(type(result))},
                    }
                )
            )
            raise InvalidAIActionOutput(result)

        log.info(
            **wrap_constants(
                message="AI node execution completed",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.NODE_ID: node_label,
                    LC.NODE_TYPE: "AINode",
                    LC.ACTION: "execute_end",
                    LC.OUTPUT_SIZE: len(result.messages),
                    LC.SUCCESS: True,
                }
            )
        )

        return result
