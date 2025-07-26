"""Root __init__.py for CrossCosmos."""
# noqa: F403

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

from .query import Query, search
from .wordlists.lafarge import LaFargeWord

# Setup logging
log_config.setup_logging(project_root)



try:
    from rich import traceback, pretty
    # traceback.install()
    pretty.install()
except ImportError:
    pass
