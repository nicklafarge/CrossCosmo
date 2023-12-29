# Standard library
import logging.config
from pathlib import Path


def setup_logging(root_path: Path):
    logging.config.fileConfig(str(root_path / "src" / "crosscosmos" / "logging_config.ini"))


logger = logging.getLogger("crosscosmos")
