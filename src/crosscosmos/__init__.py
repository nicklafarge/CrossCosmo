""" Root __init__.py for CrossCosmos.
"""

# Expose submodules
from . import (
    digraph,
    letter_utils,
    wordlists
)

# Retrieve the explicitly exported variables from crosscosmos.config
from .config import *

# Setup logging
from . import log_config

log_config.setup_logging(crosscosmos_root)
