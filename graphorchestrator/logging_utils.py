import logging
import sys


def set_logging_options(
    level: str = "INFO",
    to_file: bool = False,
    log_filename: str = "graph_orchestrator.log",
):
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="timestamp=%(asctime)s level=%(levelname)s thread=%(threadName)s module=%(module)s message=%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if to_file:
        handler = logging.FileHandler(log_filename, mode="w", encoding="utf-8")
    else:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setStream(
            open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
        )

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(handler)
