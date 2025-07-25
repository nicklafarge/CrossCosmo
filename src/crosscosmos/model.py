""" """

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScoredWord:
    word: str
    score: float
