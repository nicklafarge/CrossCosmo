""" Broda List - Trimmed by Diehl

Source (Broda):
    https://peterbroda.me/crosswords/wordlist/

Source (Diehl Trimmed List):
    https://www.facebook.com/groups/1515117638602016/files

"""

# Standard library imports
import csv
import logging
import pathlib

# Third-party imports

# Local imports
import crosscosmos as xc

logger = logging.getLogger(__name__)


def parse_word_score(word_score_path: pathlib.Path, word_model, delimiter: str):
    i = 0
    for row in xc.wordlists.parsing_utils.read_csv_generator(word_score_path, delimiter):
        if i % 100 == 0:
            print(i)
        word, score = row

        word_model(word=word, score=score)
        i += 1
