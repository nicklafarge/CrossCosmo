"""Root __init__.py for CrossCosmos."""
# ruff: noqa: F403,E402, I001

# Configuration
from .config import *

# Logging
import logging
from .log_config import setup_logging

setup_logging()
logger = logging.getLogger("crosscosmos")

# Basic classes
from .enums import *

from . import wordlists

# Expose submodules
from . import (
    constants,
    io_utils,
    letter_utils,
    log_config,
    standards,
)
from .wordlists.lafarge import LaFargeWord
from .query import Query, search
from .refine import Refiner, refine

from . import corpus, scoring

from . import grid
from .grid import Grid, Cell, Entry

from . import gui
from .archive import grid_gui
from .gui.new_grid import run_gui
from .grid_pruner import GridPruningSolver

from . import bot


try:
    from rich import traceback, pretty

    # traceback.install()
    pretty.install()
except ImportError:
    pass
