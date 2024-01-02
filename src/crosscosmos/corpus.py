"""
Copyright 2023 The Johns Hopkins University Applied Physics Laboratory LLC (JHU/APL).

All Rights Reserved.
This material may be only be used, modified, or reproduced by or for the U.S. Government
pursuant to the license rights granted under the clauses at DFARS 252.227-7013/7014 or
FAR 52.227-14. For any other permission, please contact the Office of Technology Transfer at JHU/APL.
"""

# Standard library imports
import logging
from typing import List
import re

# Third-party imports
import pygtrie

# Local imports
from crosscosmos.data_models.lafarge_model import LaFargeWord
from crosscosmos import letter_utils

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


class Corpus(object):

    def __init__(self, word_list: List[LaFargeWord]):
        self.word_list = word_list
        self.trie = self.build_trie()

    def __getitem__(self, position):
        return self.word_list[position]

    def __repr__(self):
        return f"CrossCosmos.Corpus(n={len(self.word_list)})"

    @classmethod
    def from_lafarge_db(cls):
        words = [w for w in LaFargeWord.select() if
                 not letter_utils.has_numbers(w.word)
                 and len(w.word) >= 3
                 ]
        return cls(words)

    def to_n_letter_corpus(self, n: int):
        assert 3 <= n <= 22

        return Corpus([w for w in self.word_list if len(w.word) == n])

    def query(self, query_str: str) -> List[LaFargeWord]:
        query_pattern = fr"\b{query_str.replace("?", AZRE_PATTERN)}\b"
        compiled_pattern = re.compile(query_pattern, re.IGNORECASE)
        matching = [w for w in self.word_list if compiled_pattern.search(w.word)]
        return sorted(matching, key=lambda w: w.collab_score or 0, reverse=True)

    def build_trie(self) -> pygtrie.CharTrie:
        t = pygtrie.CharTrie()
        for lw in self.word_list:
            t[lw.word] = True
        return t

    def subtree(self, prefix: str, as_corpus=True):
        try:
            subree_words = [x[0] for x in self.trie.items(prefix)]
        except KeyError:
            return []

        if as_corpus:
            return Corpus([w for w in LaFargeWord.select() if w.word in subree_words])
        else:
            return subree_words

    def str2laf(self, word: str):
        return LaFargeWord.select(lambda w: w.word == word)
