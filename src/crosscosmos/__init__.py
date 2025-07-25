"""Root __init__.py for CrossCosmos."""

# Retrieve the explicitly exported variables from crosscosmos.config
# Expose submodules
from . import (
    constants,
    corpus,
    grid,
    gui,
    io_utils,
    letter_utils,
    log_config,
    query,
    standards,
    wordlists,
)

# Enums
from .bot import LetterSequenceStatus, LetterStatus
from .config import *
from .filter import Filter
from .grid import (
    CellStatus,
    GridDirection,
    GridStatus,
    GridSymmetry,
    MoveDirection,
    WordDirection,
)
from .gui.grid_gui import run_default as run_gui
from .query import Query, search
from .wordlists.lafarge import LaFargeWord

# Setup logging
log_config.setup_logging(project_root)
