"""Broda List - Trimmed by Diehl

Source (Broda):
    https://peterbroda.me/crosswords/wordlist/

Source (Diehl Trimmed List):
    https://www.facebook.com/groups/1515117638602016/files

Source (Spread the word list):
    https://www.spreadthewordlist.com/wordlist

"""

import logging
import pathlib

import crosscosmos as xc

logger = logging.getLogger(__name__)


def parse_word_score(word_score_path: pathlib.Path, word_model, delimiter: str, score_multiplier: int = 1):
    i = 0
    for row in xc.wordlists.parsing_utils.read_csv_generator(word_score_path, delimiter):
        if i % 1000 == 0:
            print(i)
        word, score = row

        word_model(word=word, score=int(int(score) * score_multiplier))
        i += 1
