""" Data models for letters and words
"""

# Standard library imports
import logging
from typing import Union

# Third-party imports
import networkx as nx
from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict
)

# Local imports
import crosscosmos as xc

logger = logging.getLogger(__name__)


class Letter(BaseModel, frozen=True):
    s: str = ConfigDict()
    i: int
    j: int


class Word(BaseModel):
    word: str
    info: AnyUrl
    pubid: str = None


