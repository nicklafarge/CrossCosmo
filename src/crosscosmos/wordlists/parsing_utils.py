""" Helper utilities for parsing databases
"""

# Standard library imports
import csv
import logging
import pathlib

# Third-party imports
import numpy as np

# Local imports

logger = logging.getLogger(__name__)


def read_csv_generator(path: pathlib.Path, delimiter: str, **kwargs):
    with open(path, "r") as file:
        reader = csv.reader(file, delimiter=delimiter, **kwargs)

        for row in reader:
            yield row
