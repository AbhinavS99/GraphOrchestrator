import contextvars
from typing import Dict, Any

# Create a context variable to store logging context data.
# This allows us to store and retrieve contextual data within the execution flow.
_log_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "log_context", default={}  # Set the default value as an empty dictionary.
)


class LogContext:
    """
    A utility class to manage the logging context using contextvars.
    """

    @staticmethod
    def set(context: Dict[str, Any]) -> None:
        """
        Sets the current execution context.
        Args:
            context: A dictionary containing key-value pairs representing the context (e.g., run_id, graph_name).
        """
        _log_context.set(context)  # Set the provided context into the context variable.

    @staticmethod
    def get() -> Dict[str, Any]:
        """Returns the current execution context."""
        return (
            _log_context.get()
        )  # Get and return the current context from the context variable.

    @staticmethod
    def clear() -> None:
        """Clears the context by setting it to an empty dictionary."""
        _log_context.set({})  # Reset the context variable to an empty dictionary.
