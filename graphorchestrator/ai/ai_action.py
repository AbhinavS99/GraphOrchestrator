# Import necessary modules and classes
from abc import ABC, abstractmethod
from collections import abc
from typing import Any

# Import custom exceptions and utility classes from the graphorchestrator package
from graphorchestrator.core.state import State
from graphorchestrator.core.exceptions import InvalidAIActionOutput
from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class AIActionBase(ABC):
    """Abstract base class for defining AI actions within the graph orchestration framework.

    This class serves as a template for creating specialized nodes that can interact
    with and modify the state of a graph using an underlying AI model.

    Attributes:
        config (dict): A dictionary containing configuration parameters for the AI model.
        _model_built (bool): A flag indicating whether the AI model has been built.
        model (Any): The AI model instance.
        is_node_action (bool): A flag indicating that this object is an AI node action.
        __name__ (str): The name of the AI action, which defaults to the class name.
    """

    def __init__(self, config: dict) -> None:
        """
        Initializes an AIActionBase instance.

        Args:
            config (dict): Configuration parameters for the AI model.
        """
        # Store the provided configuration
        self.config: dict = config
        # Initialize flags and model to default states
        self._model_built = False
        self.model: Any = None
        # Identify the instance as an AI node action
        self.is_node_action = True
        # Set the name to the class name
        self.__name__ = self.__class__.__name__

        # Get the logger instance
        log = GraphLogger.get()
        # Use the class name as the node label
        node_label = self.__name__

        # Log the initialization of the AIActionBase instance
        log.info(
            **wrap_constants(
                message="AIActionBase initialized",
                **{
                    LC.EVENT_TYPE: "node",
                    LC.ACTION: "node_created",  # Action being taken: node creation
                    LC.NODE_ID: node_label,
                    LC.NODE_TYPE: "AINode",
                    LC.CUSTOM: {"config": self.config},  # Full config included here
                }
            )
        )

    @abstractmethod
    def build_model(self) -> None:
        """Build and configure the AI model.

        This method should be implemented by subclasses to handle the creation and
        configuration of the AI model. It is typically called before processing any state.

        Subclasses must set the following attributes:
            self.model: The constructed AI model instance.
            self._model_built: Set to True to indicate the model is built.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def process_state(self, state: State) -> State:
        """Process the state using the AI model.

        This is the main method where the AI model logic is applied to the current state.
        Subclasses must implement this method to define how the AI model modifies the state.

        Args:
            state (State): The current state to be processed.

        Returns:
            State: The new state after processing.
        """
        raise NotImplementedError

    async def __call__(self, state: State) -> State:
        """
        Invokes the AI action's processing logic.
        """
        # Get the logger instance and the node label
        log = GraphLogger.get()
        node_label = getattr(self, "__name__", self.__class__.__name__)

        # If the model has not been built yet, build it
        if not self._model_built:
            self.build_model()

            # Log that the AI model has been built
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

        # Log the start of the AI node execution
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

        # Process the state using the AI model
        result_or_coro = self.process_state(state)
        # Handle coroutines if needed
        result = (
            await result_or_coro
            if isinstance(result_or_coro, abc.Awaitable)
            else result_or_coro
        )

        # Validate the output
        # Ensure that the output is a State object; if not, raise an error
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

        # Log the completion of the AI node execution
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

        # Return the processed state
        return result
