# Standard library imports
import logging
from typing import List
import re

# Third party
import pony

# Local
import crosscosmos as xc
from crosscosmos.data_models.lafarge_model import lafarge_word_db, LaFargeWord
from crosscosmos.digraph.xgraph import LetterSet

logger = logging.getLogger(__name__)

TEST_WORDS = [
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

AZRE_PATTERN = "[a-zA-Z]"


def load_corpus(word_db: LaFargeWord):
    return [w for w in word_db.select() if xc.letter_utils.is_only_letters(w.word)]


def query(query_str: str, word_list: List[LaFargeWord]):
    query_pattern = fr"\b{query_str.replace("?", AZRE_PATTERN)}\b"
    compiled_pattern = re.compile(query_pattern, re.IGNORECASE)  # re.IGNORECASE makes it case-insensitive
    matching = [w for w in word_list if compiled_pattern.search(w.word)]
    return sorted(matching, key=lambda w: w.collab_score or 0, reverse=True)


# m = '??A?'
# scores = [rapidfuzz.fuzz.radio(m) for w in test_words]
# by_matching = sorted(test_words, key=lambda w: rapidfuzz.fuzz.ratio(w, m), reverse=True)
#
# rapidfuzz.process.cdist()

# rapidfuzz.process.extract(m, test_words)


pony.options.CUT_TRACEBACK = False

ls = LetterSet(3)
xg = ls.create_graph()

words = [w for w in LaFargeWord.select()]
words = [w for w in words if not xc.letter_utils.has_numbers(w.word)]

pattern = 'G???E'

compiled_pattern = re.compile(re_pattern, re.IGNORECASE)  # re.IGNORECASE makes it case-insensitive
test_words = [w.word for w in words]

for i in range(min(40, len(by_matching))):
    print(by_matching[i].verbose())
# test = rapidfuzz.process.extract(m, [w.word for w in words], scorer=rapidfuzz.fuzz.ratio)
# scores = [rapidfuzz.fuzz.ratio(m, w) for w in test_words]
# by_matching = sorted(test_words, key=lambda w: rapidfuzz.fuzz.ratio(w, m), reverse=True)
