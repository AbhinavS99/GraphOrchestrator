import json
import datetime
from typing import Optional, Any

from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class NullGraphLogger:
    """
    A no-op logger used when GraphLogger is not initialized.
    This class provides dummy implementations of logging methods that do nothing.
    It's a fallback to prevent errors when a real logger isn't available.
    """

    def info(self, *args, **kwargs):
        """Dummy info method that does nothing."""
        pass  # No operation

    def debug(self, *args, **kwargs):
        """Dummy debug method that does nothing."""
        pass  # No operation

    def error(self, *args, **kwargs):
        """Dummy error method that does nothing."""
        pass  # No operation

    def warning(self, *args, **kwargs):
        """Dummy warning method that does nothing."""
        pass  # No operation


class GraphLogger:
    """
    Singleton logger that emits structured JSON logs using wrap_constants().
    This logger writes log entries to a file or standard output.
    It formats log entries as JSON and includes a timestamp.
    """

    _instance: Optional["GraphLogger"] = None

    def __init__(self, filename: Optional[str] = None):
        """Initializes the GraphLogger with an optional filename."""
        self.filename = filename
        if filename:
            self._file = open(filename, "a", encoding="utf-8")
        else:
            import sys

            self._file = sys.stdout  # fallback to stdout if no file

    def _log(self, level: str, message: str, **kwargs: Any):
        """
        Internal method to write a log entry.
        Formats the log entry as JSON and writes it to the file.
        """
        log_entry = wrap_constants(message=message, level=level.upper(), **kwargs)
        self._file.write(json.dumps(log_entry) + "\n")
        self._file.flush()  # Ensure the log is written immediately

    def info(self, message: str, **kwargs: Any):
        """Logs a message with the INFO level."""
        self._log("INFO", message, **kwargs)

    def debug(self, message: str, **kwargs: Any):
        """Logs a message with the DEBUG level."""
        self._log("DEBUG", message, **kwargs)

    def warning(self, message: str, **kwargs: Any):
        """Logs a message with the WARNING level."""
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any):
        """Logs a message with the ERROR level."""
        self._log("ERROR", message, **kwargs)

    def close(self):
        """
        Closes the log file.
        If the output is stdout, it does not close it.
        """
        # Check if the file is not sys.stdout before closing
        if self._file != getattr(self._file, "fileno", lambda: None)():
            self._file.close()

    @classmethod
    def initialize(cls, filename: Optional[str] = None):
        """
        Initializes the singleton instance of GraphLogger.
        If called multiple times, it overrides the previous instance.
        """
        cls._instance = cls(filename)

    @classmethod
    def get(cls) -> "GraphLogger":
        """
        Returns the singleton instance of GraphLogger.
        If not initialized, returns the NullGraphLogger.
        """
        return cls._instance if cls._instance else NullGraphLogger()
