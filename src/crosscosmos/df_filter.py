""" """

import logging

import polars as pl

from crosscosmos import constants, query

logger = logging.getLogger(__name__)


class DfFilter:
    def __init__(
        self,
        df: pl.DataFrame,
        q: int = 1,
        sunday: bool = False,
        default: bool = True,
        alpha_only: bool = True,
    ):
        """Helper class for applying filters to a dataframe containing word results (see xc.Query)

        Parameters
        ----------
        df : pl.DataFrame
            Database containing word data
        """
        self._df = df.clone()

        if alpha_only:
            self.alpha_only()

        if default:
            min_score = q * 20
            self.default(
                min_score=min_score, max_len=constants.NYT_REGULAR_SIZE if not sunday else constants.NYT_SUNDAY_SIZE
            )

    def default(self, min_len: int = 3, max_len: int = constants.NYT_REGULAR_SIZE, min_score: float = 1) -> "DfFilter":
        """Sets default query parameters:

        Defaults:
            - 3+ letter words
            - Word length less than puzzle size (default=15)
            - Score > 0

        Parameters
        ----------
        min_len : int, optional, default=3
            Minimum word length
        max_len : int, optional, default=15
            Maximum word length
        min_score : float, optional, default=1
            Minimum word score
        """
        self.min_length(min_len)
        self.max_length(max_len)
        self.min_score(min_score)
        return self

    def alpha_only(self):
        """Filter word list to remove words with symbols or numbers"""
        self._df = self._df.filter(pl.col("word").str.contains(rf"^{constants.ANY_LETTER_RE_PATTERN}+$"))

    def fix_letter(self, letter_idx: int, value: str) -> "DfFilter":
        """Filter to words that contain a given value at the specified index"""
        assert len(value) == 1
        self._df = self._df.filter(pl.col("word").str.slice(letter_idx, 1) == value)
        return self

    def length(self, word_len: int | tuple[int, int]) -> "DfFilter":
        """Filter to only words of a specified length"""
        if isinstance(word_len, int):
            self._df = self._df.filter(pl.col("word").str.len_chars() == word_len)
        elif isinstance(word_len, tuple) and len(word_len) == 2:
            self.min_length(word_len[0])
            self.max_length(word_len[1])
        else:
            raise ValueError(f"Unexpected input: {word_len}")
        return self

    def min_length(self, word_len: int) -> "DfFilter":
        """Filter to words greater than or equal to a given length"""
        self._df = self._df.filter(pl.col("word").str.len_chars() >= word_len)
        return self

    def max_length(self, word_len: int) -> "DfFilter":
        """Filter to words less than or equal to a given length"""
        self._df = self._df.filter(pl.col("word").str.len_chars() <= word_len)
        return self

    def min_score(self, min_score: float) -> "DfFilter":
        """Filter results to all be above a minimum score value"""
        self._df = self._df.filter(pl.col("score") >= min_score)
        return self

    def max_score(self, max_score: float) -> "DfFilter":
        """Filter results to all be above a maximum score value"""
        self._df = self._df.filter(pl.col("score") <= max_score)
        return self

    def match(self, match_str: str) -> "DfFilter":
        """
        Match words against a pattern string with wildcards:
        ? - any single letter
        * - any number of letters (0 or more)
        # - consonant
        @ - vowel

        Supports repetition: ?[4], #[3], @[2]
        """
        match_str = query.expand_match_pattern(match_str)
        re_pattern = query.create_match_regex(match_str)
        self._df = self._df.filter(pl.col("word").str.contains(re_pattern))
        return self

    def sort_by_score(self):
        """ Sorts the data frame by the score value
        """
        self._df = self._df.sort(by="score", descending=True)
        return self

    def apply(self) -> pl.DataFrame:
        return self._df

    def df(self) -> pl.DataFrame:
        return self._df

    def alphabetical(self) -> pl.DataFrame:
        return self._df.sort(by="word")

    def by_score(self) -> pl.DataFrame:
        return self.sort_by_score().df()


def refine(
    df: pl.DataFrame,
    match_term: str | None = None,
    fixed_letters: dict[int, str] | None = None,
    length: int | None = None,
    min_score: int | None = None,
    **kwargs,
) -> pl.DataFrame:
    df_filter = DfFilter(df, **kwargs)
    if match_term:
        df_filter = df_filter.match(match_term)
    if length:
        df_filter = df_filter.length(length)
    if min_score:
        df_filter = df_filter.min_score(min_score)

    fixed_letters = fixed_letters or {}
    for k, v in fixed_letters.items():
        df_filter = df_filter.fix_letter(k, v)

    return df_filter.by_score()
