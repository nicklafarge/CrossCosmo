"""Root __init__.py for CrossCosmos."""

# Retrieve the explicitly exported variables from crosscosmos.config
from .config import *

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
    smatch,
    standards,
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
log_config.setup_logging(project_root)
