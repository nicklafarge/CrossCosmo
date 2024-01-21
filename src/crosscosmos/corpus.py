# Standard library imports
import logging
from typing import List
import re

# Third-party imports
import pygtrie

# Local imports
from crosscosmos.data_models.lafarge_model import LaFargeWord
from crosscosmos.data_models.diehl_model import DiehlWord, TestWord
from crosscosmos import letter_utils

logger = logging.getLogger(__name__)

AZRE_PATTERN = "[a-zA-Z]"


class Corpus(object):

    def __init__(self, word_list: List[LaFargeWord]):
        self.word_list = word_list
        self.trie = None

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

    @classmethod
    def from_test(cls):
        return cls([w for w in TestWord.select()])

    @classmethod
    def from_diehl(cls):
        return cls([w for w in DiehlWord.select()])

    def to_n_letter_corpus(self, n: int):
        return self.to_subcorpus(n, n)

    def to_subcorpus(self, n: int, m: int):
        assert 3 <= n <= 22
        assert 3 <= m <= 22
        assert m >= n

        return Corpus([w for w in self.word_list if n <= len(w.word) <= m])

    def to_n_tries(self, n, padded=False):
        assert n >= 3
        tries = [self.to_n_letter_corpus(i).to_trie() for i in range(3, n+1)]
        if padded:
            return [None] * 3 + tries
        else:
            return tries

    def query(self, query_str: str) -> List[LaFargeWord]:
        query_pattern = fr"\b{query_str.replace('?', AZRE_PATTERN)}\b"
        compiled_pattern = re.compile(query_pattern, re.IGNORECASE)
        matching = [w for w in self.word_list if compiled_pattern.search(w.word)]
        return sorted(matching, key=lambda w: w.collab_score or 0, reverse=True)

    def build_trie(self):
        self.trie = self.to_trie()

    def to_trie(self) -> pygtrie.CharTrie:
        t = pygtrie.CharTrie()
        for lw in self.word_list:
            t[lw.word] = True
        return t

    def subtree(self, prefix: str, as_corpus=True):
        if not self.trie:
            self.build_trie()

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


if __name__ == '__main__':
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
