"""Root __init__.py for CrossCosmos."""
# ruff: noqa: F403,E402, I001

# Configuration
from .config import crosscosmos_root, project_root

# Logging
import logging
from .log_config import setup_logging

setup_logging(project_root)
logger = logging.getLogger("crosscosmos")

# Basic classes
from .enums import *

from . import wordlists

# Expose submodules
from . import (
    corpus,
    constants,
    grid,
    gui,
    io_utils,
    letter_utils,
    log_config,
    query,
    standards,
)


from .query import Query, search
from .wordlists.lafarge import LaFargeWord
from .df_filter import DfFilter, refine

from .gui import grid_gui

from . import bot


try:
    from rich import traceback, pretty

    # traceback.install()
    pretty.install()
except ImportError:
    pass
