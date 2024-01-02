""" Utilities for manipulating letters
"""

# Standard library imports
import itertools
import logging
import re

# Third-party imports

# Local imports

logger = logging.getLogger(__name__)


def char2int(letter: str) -> int:
    return ord(letter.upper()) - 65


def int2char(idx: int) -> str:
    return chr(idx + 65)


def is_only_letters(input_string: str):
    return bool(re.fullmatch(r"^[a-zA-Z]+$", input_string))


def has_numbers(inputString: str):
    return any(char.isdigit() for char in inputString)


def generate_permutations(word: str):
    # Create a list of tuples, each containing the character and a placeholder
    choices = [(char, '?') for char in word]

    # Use itertools.product to generate all combinations of characters and placeholders
    for combination in itertools.product(*choices):
        # Join the characters in the combination to form a string
        yield ''.join(combination)


ALPHABET = [int2char(i) for i in range(26)]
