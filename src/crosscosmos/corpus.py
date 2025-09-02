import logging
from itertools import chain

import polars as pl
import pygtrie

from crosscosmos import constants, load_xc_wordlist
from crosscosmos.enums import ModelSource
from crosscosmos.refine import Refiner

logger = logging.getLogger(__name__)

WORD_SCORE_LIST_TYPE = list[tuple[str, float]]
WORD_INDEX_MAP_TYPE = dict[int, dict[int, dict[str, WORD_SCORE_LIST_TYPE]]]


def initialize_word_index_map(max_len: int) -> WORD_INDEX_MAP_TYPE:
    """Creates an empty nested dictionary mapping word lengths to positions to characters to indices."""
    word_idx_map = {}
    for word_len in range(1, max_len + 1):
        word_idx_map[word_len] = {}
        for pos in range(max_len):
            word_idx_map[word_len][pos] = {char: [] for char in constants.ALPHABET}
    return word_idx_map


def create_word_index_map(df: pl.DataFrame) -> WORD_INDEX_MAP_TYPE:
    """Creates a word index map

    E.g., for 4-letter words that being with "A":
    4: {
      0: {
        "A": []
      }
    }

    Parameters
    ----------
    df : DataFrame containing words/scores to generate the index map

    Returns
    -------
    dict
        Index mapping

    """
    max_len = df["word"].str.len_chars().max()
    word_idx_map = initialize_word_index_map(max_len)

    # Populate the index map
    for w in df.iter_rows(named=True):
        for i, c in enumerate(w["word"]):
            if c not in constants.ALPHABET:
                continue
            word_idx_map[w["length"]][i][c].append((w["word"], w["score"]))

    return word_idx_map


def tuples_to_df(word_score_tuples: WORD_SCORE_LIST_TYPE) -> pl.DataFrame:
    """Converts a list of (word, score) tuples to a polars dataframe"""
    return pl.DataFrame(word_score_tuples, schema=["word", "score"])


def is_wildcard_matched(word_letter: str, wildcard: str) -> bool:
    """
    Evaluates if a letter matches a letter or wildcard character

    [A-Z] - specific character
    * - any number of letters (0 or more)
    # - consonant
    @ - vowel

    ----------
    word_letter : str
        Letter to validate
    wildcard : str
        Letter or wildcard character to match against

    Returns
    -------
    bool
        True if word_letter is valid

    """
    wildcard = wildcard.upper().strip()

    if wildcard in constants.ALPHABET:
        return word_letter == wildcard
    elif wildcard in constants.PLACEHOLDERS:
        return True
    elif wildcard == "#":
        return word_letter in constants.CONSONANTS
    elif wildcard == "@":
        return word_letter in constants.VOWELS
    else:
        raise ValueError(f"Unexpected character: {wildcard}")


class WordMap:
    def __init__(self, df: pl.DataFrame):
        """Word-index map filterer for fast word filtering"""
        self.words = create_word_index_map(df)

    def filter_by_letters(self, word_len: int, letter_location: dict[int, str] | None = None) -> pl.DataFrame:
        """
        Get words that match a specific input

        Parameters
        ----------
        word_len : int
            Length of word
        letter_location : dict[int, str]
            Dictionary mapping fixed letter locations in the query string
        Returns
        -------
        pl.DataFrame
        """

        def _all_with_length():
            return tuples_to_df(
                chain.from_iterable(
                    value for inner_dict in self.words[word_len].values() for value in inner_dict.values()
                )
            )

        if not letter_location:
            return _all_with_length()

        letter_idx, letter = next(((k, v) for k, v in letter_location.items() if v in constants.ALPHABET), (None, None))

        if not letter:
            return _all_with_length()

        return tuples_to_df(
            [
                (w, score)
                for w, score in self.words[word_len][letter_idx][letter]
                if all(
                    is_wildcard_matched(w[pos], letter) for pos, letter in letter_location.items() if pos != letter_idx
                )
            ]
        )

    def match(self, query_str: str) -> pl.DataFrame:
        """Query the wordmap based on a match string"""
        filter_idxs = {
            i: v for i, v in enumerate(query_str) if v in list(constants.ALPHABET) + constants.PLACEHOLDERS + ["#", "@"]
        }
        return self.filter_by_letters(len(query_str), filter_idxs)


class Corpus:
    def __init__(self, df: pl.DataFrame | None = None):
        self._df: pl.DataFrame = df

        if self._df is None:
            logger.info("Loading default CrossCosmos wordlist...")
            self._df = load_xc_wordlist()

        self._map: WordMap | None = None if self._df is None or self._df.is_empty() else WordMap(self._df)


    def __repr__(self):
        return f"CrossCosmos.Corpus(n={len(self.df)})"

    @property
    def df(self) -> pl.DataFrame:
        return self._df

    def query_wordmap(self, query_str: str) -> pl.DataFrame:
        """Queries the corpus using the WordMap"""
        if not self._map:
            raise ValueError("Cannot perform query: no WordMap available")
        return self._map.match(query_str)

    def query_df(self, query_str: str) -> pl.DataFrame:
        """Queries the corpus using the DataFrame"""
        if self._df is None or self._df.is_empty():
            raise ValueError("Cannot perform query: no DataFrame available")
        return Refiner(self._df, default=False, alpha_only=False).match(query_str).by_score()

    def query(self, query_str: str) -> pl.DataFrame:
        """Queries the current word list from the wordmap, dataframe, or database
        """
        if self._map:
            # Word map
            return self.query_wordmap(query_str)
        elif self._df is not None and not self._df.is_empty():
            # Dataframe
            return self.query_df(query_str)
        else:
            raise ValueError("Unable to perform query: No data available!")

class TrieCorpus:
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
    def from_collab(cls, **kwargs):
        from crosscosmos.wordlist import load_collab_wordlist
        return cls(load_collab_wordlist(), ModelSource.CollabWordList)

    @classmethod
    def from_lafarge(cls, max_length: int | None = None, **kwargs):
        from crosscosmos.wordlist import load_xc_wordlist
        return cls(load_xc_wordlist(), ModelSource.CollabWordList)

    @classmethod
    def from_diehl(cls, **kwargs):
        from crosscosmos.wordlist import load_diehl_wordlist
        return cls(load_diehl_wordlist(), ModelSource.Diehl)

    def to_n_letter_corpus(self, n: int) -> "TrieCorpus":
        """Creates a new Corpus instance containing only words of a particular length"""
        return self.to_subcorpus(n, n)

    def max_length(self, word_len: int) -> "TrieCorpus":
        """Filter to words less than or equal to a given length"""
        self._df = Refiner(self._df, default=False).max_length(word_len).df()
        return self

    def to_subcorpus(self, min_len: int, max_len: int) -> "TrieCorpus":
        """Creates a new Corpus instance containing only words between a min/max length bound"""
        assert 3 <= min_len <= constants.NYT_SUNDAY_SIZE
        assert 3 <= max_len <= constants.NYT_SUNDAY_SIZE
        assert max_len >= min_len

        sub_df = Refiner(self._df, default=False).length((min_len, max_len)).df()
        return TrieCorpus(sub_df, self.model)

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
        return Refiner(self._df, default=False).match(query_str).by_score()

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
            return TrieCorpus(sub_df, self.model)

        return sub_df


if __name__ == "__main__":
    df = query.search("?????", limit=None)
    _map = WordMap(df)

    q1 = _map.filter_by_letters(5, {2: "A", 3: "@"})
    q11 = _map.match("--A@-")
    q2 = _map.filter_by_letters(5, {2: "@", 3: "A"})
    q21 = _map.match("--@A-")
    q3 = _map.filter_by_letters(5)
    q31 = _map.match("-----")
    q32 = _map.filter_by_letters(5, dict.fromkeys(range(5), "-"))

    corpus = Corpus(df=df)
    print(corpus.query("--@AD"))