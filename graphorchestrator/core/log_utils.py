import datetime
import threading
from typing import Any, Dict

from graphorchestrator.core.log_context import LogContext
from graphorchestrator.core.log_constants import LogConstants as LC


def wrap_constants(message: str, level: str = "INFO", **kwargs: Any) -> Dict[str, Any]:
    """
    Constructs a structured log entry including metadata from LogContext.

    Args:
        message (str): Human-readable log message.
        level (str): Logging level (INFO, DEBUG, etc.)
        kwargs: Any additional log fields (e.g. node_id, action, custom).

    Returns:
        dict: JSON-compatible structured log dictionary.
    """
    base = {
        LC.TIMESTAMP: datetime.datetime.utcnow().isoformat(timespec="milliseconds")
        + "Z",
        LC.LEVEL: level.upper(),
        LC.MESSAGE: message,
        LC.THREAD: threading.current_thread().name,
    }

    # Merge LogContext and dynamic fields (explicit kwargs take precedence)
    base.update(LogContext.get())
    base.update(kwargs)

    return {
        (k.value if isinstance(k, LC) else str(k)): v
        for k, v in base.items()
        if v is not None
    }
