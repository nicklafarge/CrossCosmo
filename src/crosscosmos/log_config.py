from importlib import resources
import logging.config
from pathlib import Path


def setup_logging():
    logging.config.fileConfig(
        str(resources.files("crosscosmos") /"logging_config.ini")
    )


__all__ = ["setup_logging"]
