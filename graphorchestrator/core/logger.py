import json
import datetime
from typing import Optional, Any

from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC


class NullGraphLogger:
    """A no-op logger used when GraphLogger is not initialized."""

    def info(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass


class GraphLogger:
    """
    Singleton logger that emits structured JSON logs using wrap_constants().
    """

    _instance: Optional["GraphLogger"] = None

    def __init__(self, filename: Optional[str] = None):
        self.filename = filename
        if filename:
            self._file = open(filename, "a", encoding="utf-8")
        else:
            import sys

            self._file = sys.stdout  # fallback to stdout if no file

    def log(self, level: str, message: str, **kwargs: Any):
        log_entry = wrap_constants(message=message, level=level.upper(), **kwargs)
        self._file.write(json.dumps(log_entry) + "\n")
        self._file.flush()

    def info(self, message: str, **kwargs: Any):
        self.log("INFO", message, **kwargs)

    def debug(self, message: str, **kwargs: Any):
        self.log("DEBUG", message, **kwargs)

    def warning(self, message: str, **kwargs: Any):
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any):
        self.log("ERROR", message, **kwargs)

    def close(self):
        if (
            self._file != getattr(self._file, "fileno", lambda: None)()
        ):  # skip sys.stdout
            self._file.close()

    @classmethod
    def initialize(cls, filename: Optional[str] = None):
        cls._instance = cls(filename)

    @classmethod
    def get(cls) -> "GraphLogger":
        return cls._instance if cls._instance else NullGraphLogger()
