import contextvars
from typing import Dict, Any

_log_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "log_context", default={}
)


class LogContext:
    @staticmethod
    def set(context: Dict[str, Any]) -> None:
        """Sets the current execution context (e.g., run_id, graph_name, etc.)"""
        _log_context.set(context)

    @staticmethod
    def get() -> Dict[str, Any]:
        """Returns the current execution context"""
        return _log_context.get()

    @staticmethod
    def clear() -> None:
        """Clears the context explicitly if needed (optional utility)"""
        _log_context.set({})
