
# Standard library imports
import logging
from typing import Union

# Third party
import networkx as nx
from pydantic import (
    BaseModel,
    ConfigDict
)
import pygtrie
# Local
import crosscosmos as xc

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


test_words = [
    'SKIP',
    'JUMP',
    'HELP',
    'FLOP',
    'SLOW',
    'HAND',
    'SLAP',
    'LUMP',
    'LEAP'
]

t = pygtrie.CharTrie()
for s in test_words:
    t[s] = True
