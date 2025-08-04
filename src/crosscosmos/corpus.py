import logging

import polars as pl
import pygtrie

from crosscosmos import constants, query
from crosscosmos.enums import ModelSource

logger = logging.getLogger(__name__)


class Corpus:
    def __init__(self, df: pl.DataFrame, model: ModelSource):
        self._df = df
        self.trie = None
        self.model = model

    def __getitem__(self, position):
        return self.df[position]

    def __repr__(self):
        return f"CrossCosmos.Corpus(n={len(self.df)})"

    @property
    def df(self):
        return self._df

    @df.setter
    def df(self, new_df):
        self._df = new_df

    @classmethod
    def from_crossword_tracker(cls, **kwargs):
        from crosscosmos.wordlists.crossword_tracker import XwordWord

        logger.info("Loading crossword tracker ...")
        words = query.Query(XwordWord, **kwargs).df()
        return cls(words, ModelSource.CrosswordTracker)

    @classmethod
    def from_collab(cls, **kwargs):
        from crosscosmos.wordlists.collaborative_wordlist import CollabWordListWord

        logger.info("Loading collab list ...")
        words = query.Query(CollabWordListWord, **kwargs).df()
        return cls(words, ModelSource.CollabWordList)

    @classmethod
    def from_lafarge(cls, max_length: int | None = None, **kwargs):
        kwargs.setdefault("limit", None)
        from crosscosmos.wordlists.lafarge import LaFargeWord

        logger.info("Loading LaFarge...")
        q = query.Query(LaFargeWord, **kwargs)
        if max_length:
            q.max_length(max_length)
        return cls(q.df(), ModelSource.LaFarge)

    @classmethod
    def from_diehl(cls, **kwargs):
        from crosscosmos.wordlists.diehl import DiehlWord

        logger.info("Loading Diehl...")
        words = query.Query(DiehlWord, **kwargs).df()
        return cls(words, ModelSource.Diehl)

    def to_n_letter_corpus(self, n: int) -> "Corpus":
        """Creates a new Corpus instance containing only words of a particular length"""
        return self.to_subcorpus(n, n)

    def max_length(self, word_len: int) -> "Corpus":
        """Filter to words less than or equal to a given length"""
        self._df = refineRefiner(self._df, default=False).max_length(word_len).df()
        return self

    def to_subcorpus(self, min_len: int, max_len: int) -> "Corpus":
        """Creates a new Corpus instance containing only words between a min/max length bound"""
        assert 3 <= min_len <= constants.NYT_SUNDAY_SIZE
        assert 3 <= max_len <= constants.NYT_SUNDAY_SIZE
        assert max_len >= min_len

        sub_df = refineRefiner(self._df, default=False).length((min_len, max_len)).df()
        return Corpus(sub_df, self.model)

    def to_n_tries(self, n: int, padded: bool = False) -> list[pygtrie.CharTrie]:
        """Constructs 'n' trie instances for sequential word lengths, starting at 3.

        Parameters
        ----------
        n : int
            Number of tries to create, starting at 3
        padded : bool, optional
            If true, insert 'None' values at the beginning of the returned list (for indices 0,1,2)

        Returns
        -------
        list of pygtrie.CharTrie:
            List of create trie objects
        """
        assert n >= 3

        tries = [self.to_n_letter_corpus(i).to_trie() for i in range(3, n + 1)]
        return [None, None, None, *tries] if padded else tries

    def query(self, query_str: str) -> pl.DataFrame:
        """Queries the current word list"""
        return refineRefiner(self._df, default=False).match(query_str).by_score()

    def build_trie(self):
        """Updates the 'trie' variable with values from the current word list"""
        self.trie = self.to_trie()

    def to_trie(self) -> pygtrie.CharTrie:
        """Construct a trie from the current word list"""
        t = pygtrie.CharTrie()
        for row in self.df.iter_rows(named=True):
            t[row["word"]] = True
        return t

    def subtree(self, prefix: str, as_corpus: bool = True):
        """Uses the trie to extract words that exist given a particular prefix"""
        if not self.trie:
            self.build_trie()

        try:
            subree_words = [x[0] for x in self.trie.items(prefix)]
        except KeyError:
            return []

        sub_df = self.df.filter(pl.col("word").str in subree_words)
        if as_corpus:
            return Corpus(sub_df, self.model)

        return sub_df


if __name__ == "__main__":
    TEST_WORDS = [
        "SKIP",
        "JUMP",
        "HELP",
        "FLOP",
        "SLOW",
        "HAND",
        "SLAP",
        "LUMP",
        "LEAP",
    ]
