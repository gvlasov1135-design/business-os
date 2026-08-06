import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from config.settings import get_settings


def setup_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
    )
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())
