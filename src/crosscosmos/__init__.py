"""Root __init__.py for CrossCosmos."""

# Retrieve the explicitly exported variables from crosscosmos.config
from .config import *

PLACEHOLDERS = [r"?", r"-", r" "]

# Expose submodules
from . import (
    corpus,
    data_models,
    digraph,
    grid,
    gui,
    io_utils,
    letter_utils,
    log_config,
    query,
    smatch,
    standards,
    wordlists,
)

# Enums
from .bot import LetterSequenceStatus, LetterStatus
from .grid import (
    CellStatus,
    GridDirection,
    GridStatus,
    GridSymmetry,
    MoveDirection,
    WordDirection,
)

# Setup logging

log_config.setup_logging(crosscosmos_project_root)
