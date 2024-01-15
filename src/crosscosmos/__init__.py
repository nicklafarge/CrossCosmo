""" Root __init__.py for CrossCosmos.
"""

# Retrieve the explicitly exported variables from crosscosmos.config
from .config import *

# Expose submodules
from . import (
    corpus,
    data_models,
    digraph,
    gui,
    letter_utils,
    log_config,
    standards,
    smatch,
    wordlists
)

# Setup logging
from . import log_config

log_config.setup_logging(crosscosmos_project_root)
