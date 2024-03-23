# Standard library imports
import logging
from typing import List, Tuple, Union
import re
from enum import Enum

# Third-party imports
import pygtrie

# Local imports
from crosscosmos.data_models.xword_tracker_model import XwordWord
from crosscosmos.data_models.collab_word_list_model import CollabWordListWord
from crosscosmos.data_models.lafarge_model import LaFargeWord
from crosscosmos.data_models.diehl_model import DiehlWord, TestWord
# from crosscosmos.data_models.xword_tracker_model import 
from crosscosmos import letter_utils

logger = logging.getLogger(__name__)

AZRE_PATTERN = "[a-zA-Z]"
PLACEHOLDERS = [r"?", r"-", r" "]


class ModelSource(Enum):
    Test = 1
    Diehl = 2
    LaFarge = 3
    CrosswordTracker = 4
    CollabWordList = 5


score = {
    ModelSource.Test: lambda w: w.score,
    ModelSource.Diehl: lambda w: w.score,
    ModelSource.LaFarge: lambda w: w.collab_score,
    ModelSource.CrosswordTracker: lambda w: 0  # Undefined
}


class Corpus(object):

    def __init__(self, word_list, model: ModelSource):
        self.word_list = word_list
        self.trie = None
        self.model = model

    def __getitem__(self, position):
        return self.word_list[position]

    def __repr__(self):
        return f"CrossCosmos.Corpus(n={len(self.word_list)})"

    @classmethod
    def from_crossword_tracker(cls):
        logger.info("Loading crossword tracker ...")
        words = [w for w in XwordWord.select() if
                 not letter_utils.has_numbers(w.word)
                 and len(w.word) >= 3
                 ]
        return cls(words, ModelSource.CrosswordTracker)

    @classmethod
    def from_collab(cls):
        logger.info("Loading collab list ...")
        words = [w for w in CollabWordListWord.select() if
                 not letter_utils.has_numbers(w.word)
                 and len(w.word) >= 3
                 ]
        return cls(words, ModelSource.CollabWordList)

    @classmethod
    def from_lafarge(cls):
        logger.info("Loading LaFarge...")
        words = [w for w in LaFargeWord.select() if
                 not letter_utils.has_numbers(w.word)
                 and len(w.word) >= 3
                 ]
        return cls(words, ModelSource.LaFarge)

    @classmethod
    def from_test(cls):
        logger.info("Loading Test...")
        return cls([w for w in TestWord.select()], ModelSource.Test)

    @classmethod
    def from_diehl(cls):
        logger.info("Loading Diehl...")
        return cls([w for w in DiehlWord.select()], ModelSource.Diehl)

    def to_n_letter_corpus(self, n: int):
        return self.to_subcorpus(n, n)

    def to_subcorpus(self, n: int, m: int):
        assert 3 <= n <= 22
        assert 3 <= m <= 22
        assert m >= n

        return Corpus([w for w in self.word_list if n <= len(w.word) <= m], self.model)

    def to_n_tries(self, n, padded=False):
        assert n >= 3
        tries = [self.to_n_letter_corpus(i).to_trie() for i in range(3, n + 1)]
        if padded:
            return [None] * 3 + tries
        else:
            return tries

    def query(self, query_str: str) -> List[LaFargeWord]:
        # Replace placeholder {"?", "-", " "} with regular expression
        for p in PLACEHOLDERS:
            query_str = query_str.replace(p, AZRE_PATTERN)

        # Construct/compile query
        query_pattern = fr"\b{query_str}\b"
        compiled_pattern = re.compile(query_pattern, re.IGNORECASE)

        # Get all matching entries from corpus
        matching = [w for w in self.word_list if compiled_pattern.search(w.word)]

        # Return the list sorted alphebetically
        return sorted(matching, key=lambda w: score[self.model](w) or 0, reverse=True)

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

    def match(self, word_len: int, letters_with_idxs: List[Tuple[int, str]]):
        word_list = []
        for w in self.word_list:
            if len(w.word) == word_len and all([w.word[i] == c for i, c in letters_with_idxs]):
                word_list.append(w)

        return word_list


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
