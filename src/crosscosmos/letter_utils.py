""" Utilities for manipulating letters
"""

# Standard library imports
import logging

# Third-party imports

# Local imports

logger = logging.getLogger(__name__)


def char2int(letter: str) -> int:
    return ord(letter.upper()) - 65


def int2char(idx: int) -> str:
    return chr(idx + 65)


ALPHABET = [int2char(i) for i in range(26)]
