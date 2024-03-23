""" Root __init__.py for CrossCosmos.
"""

# Retrieve the explicitly exported variables from crosscosmos.config
from .config import *

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
    standards,
    smatch,
    wordlists
)

# Enums
from .bot import (
    LetterStatus,
    LetterSequenceStatus
)
from .grid import (
    CellStatus,
    GridDirection,
    GridStatus,
    WordDirection,
    GridSymmetry,
    MoveDirection
)

# Setup logging
from . import log_config

log_config.setup_logging(crosscosmos_project_root)
