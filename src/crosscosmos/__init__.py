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
    corpus,
    constants,
    grid,
    gui,
    io_utils,
    letter_utils,
    log_config,
    standards,
)

from .grid import Grid, Cell, Entry
from .query import Query, search
from .wordlists.lafarge import LaFargeWord
from .refine import Refiner, WordMap, refine
from . import scoring

from .gui import grid_gui
from .gui.new_grid import run_gui
from .grid_pruner import GridPruningSolver

from . import bot


try:
    from rich import traceback, pretty

    # traceback.install()
    pretty.install()
except ImportError:
    pass
