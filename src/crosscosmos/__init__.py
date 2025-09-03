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


# Expose submodules
from . import (
    constants,
    io_utils,
    letter_utils,
    log_config,
    standards,
)
from .refiner import Refiner, refine
from .wordlist import (
    load_collab_wordlist,
    load_crosserville_wordlist,
    load_diehl_wordlist,
    load_expanded_names_wordlist,
    load_spread_the_word_wordlist,
    load_xc_wordlist,
)

from . import corpus, scoring

from .corpus import Corpus, WordMap

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
