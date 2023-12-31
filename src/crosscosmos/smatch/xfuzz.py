
# Standard library imports
import logging
from typing import Union

# Third party
from pydantic import (
    BaseModel,
    ConfigDict
)
import rapidfuzz

# Local
import crosscosmos as xc

logger = logging.getLogger("xfuzz")
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

# test = rapidfuzz.process(test_words)

m = '??A?'
# scores = [rapidfuzz.fuzz.radio(m) for w in test_words]
# by_matching = sorted(test_words, key=lambda w: rapidfuzz.fuzz.ratio(w, m), reverse=True)
#
# rapidfuzz.process.cdist()

rapidfuzz.process.extract(m, test_words)