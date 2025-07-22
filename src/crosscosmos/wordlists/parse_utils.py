"""Parsing utilities"""

import csv
import logging
import pathlib

logger = logging.getLogger(__name__)


def read_csv_generator(path: pathlib.Path, delimiter: str, **kwargs):
    with open(path) as file:
        yield from csv.reader(file, delimiter=delimiter, **kwargs)


def parse_word_score(word_score_path: pathlib.Path, word_model, delimiter: str, score_multiplier: int = 1):
    i = 0
    for row in read_csv_generator(word_score_path, delimiter):
        if i % 1000 == 0:
            print(i)
        word, score = row

        word_model(word=word, score=int(int(score) * score_multiplier))
        i += 1
