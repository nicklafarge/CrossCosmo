"""Helper utilities for parsing databases"""

import csv
import logging
import pathlib

logger = logging.getLogger(__name__)


def read_csv_generator(path: pathlib.Path, delimiter: str, **kwargs):
    with open(path) as file:
        yield from csv.reader(file, delimiter=delimiter, **kwargs)
