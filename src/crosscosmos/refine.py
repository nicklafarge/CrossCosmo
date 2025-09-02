""" """

import logging
import re

import polars as pl

from crosscosmos import constants

logger = logging.getLogger(__name__)

def expand_match_pattern(pattern: str):
    """
    Expand pattern with repetition syntax into full pattern.
    Examples: ?[4] -> ????, #[3] -> ###
    """
    pattern = str(pattern).upper().strip()

    # Match repetition patterns like ?[4], #[3], @[2]
    repetition_pattern = r"([?#@])(\[(\d+)\])"

    def replacer(match):
        char = match.group(1)
        count = int(match.group(3))
        return char * count

    return re.sub(repetition_pattern, replacer, pattern)


def create_match_regex(match_str: str) -> str:
    """
    Handle patterns with * wildcard using regex.
    """
    # Build regex pattern
    regex_parts = []
    i = 0

    while i < len(match_str):
        c = match_str[i]

        if c in constants.PLACEHOLDERS:
            regex_parts.append(constants.ANY_LETTER_RE_PATTERN)
        elif c == "*":
            regex_parts.append(f"{constants.ANY_LETTER_RE_PATTERN}*")
        elif c == "#":
            regex_parts.append(f"[{constants.CONSONANTS}]")
        elif c == "@":
            regex_parts.append(f"[{constants.VOWELS}]")
        else:
            regex_parts.append(re.escape(c))

        i += 1
    regex_pattern = "^" + "".join(regex_parts) + "$"
    return regex_pattern

class Refiner:
    def __init__(
        self,
        df: pl.DataFrame,
        q: int | None = None,
        alpha_only: bool = False,
    ):
        """Helper class for applying filters to a dataframe containing word results (see xc.Query)

        TODO - find a way to avoid copies here

        Parameters
        ----------
        df : pl.DataFrame
            Database containing word data
        """
        self._df: pl.DataFrame = df

        if alpha_only:
            self.alpha_only()

        if q is not None:
            self.min_score(q * 20)

    def default(self, min_len: int = 3, max_len: int = constants.NYT_REGULAR_SIZE, min_score: float = 1) -> "Refiner":
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

    def alpha_only(self) -> "Refiner":
        """Filter word list to remove words with symbols or numbers"""
        self._df = self._df.filter(pl.col("word").str.contains(rf"^{constants.ANY_LETTER_RE_PATTERN}+$"))
        return self

    def fix_letter(self, letter_idx: int, value: str | list[str]) -> "Refiner":
        """Filter to words that contain a given value at the specified index"""
        self._df = self._df.filter(pl.col("word").str.slice(letter_idx, 1).is_in(list(value)))
        return self

    def length(self, word_len: int | tuple[int, int]) -> "Refiner":
        """Filter to only words of a specified length"""
        if isinstance(word_len, int):
            self._df = self._df.filter(pl.col("word").str.len_chars() == word_len)
        elif isinstance(word_len, tuple) and len(word_len) == 2:
            self.min_length(word_len[0])
            self.max_length(word_len[1])
        else:
            raise ValueError(f"Unexpected input: {word_len}")
        return self

    def min_length(self, word_len: int) -> "Refiner":
        """Filter to words greater than or equal to a given length"""
        self._df = self._df.filter(pl.col("word").str.len_chars() >= word_len)
        return self

    def new_to_nyt_only(self) -> "Refiner":
        """Filter to entries that have never appeared in the NYT
        """
        if "in_nyt" not in self._df.columns:
            raise ValueError("Column not found: 'in_nyt'")
        self._df = self._df.filter(~pl.col("in_nyt"))
        return self

    def max_length(self, word_len: int) -> "Refiner":
        """Filter to words less than or equal to a given length"""
        self._df = self._df.filter(pl.col("word").str.len_chars() <= word_len)
        return self

    def min_score(self, min_score: float) -> "Refiner":
        """Filter results to all be above a minimum score value"""
        self._df = self._df.filter(pl.col("score") >= min_score)
        return self

    def max_score(self, max_score: float) -> "Refiner":
        """Filter results to all be above a maximum score value"""
        self._df = self._df.filter(pl.col("score") <= max_score)
        return self

    def match(self, match_str: str) -> "Refiner":
        """
        Match words against a pattern string with wildcards:
        ? - any single letter
        * - any number of letters (0 or more)
        # - consonant
        @ - vowel

        Supports repetition: ?[4], #[3], @[2]
        """
        match_str = expand_match_pattern(match_str)
        re_pattern = create_match_regex(match_str)
        self._df = self._df.filter(pl.col("word").str.contains(re_pattern))
        return self

    def sort_by_score(self) -> "Refiner":
        """Sorts the data frame by the score value"""
        self._df = self._df.sort(by="score", descending=True)
        return self

    def count(self) -> int:
        return len(self._df)

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
    max_length: int | None = None,
    min_length: int | None = None,
    min_score: float | None = None,
    new_to_nyt : bool | None = None,
    **kwargs,
) -> pl.DataFrame:
    """
    Refines a polars DataFrame containing a scored wordlist

    Parameters
    ----------
    df : pl.DataFrame
        Data frame containing a scored wordlist with "word" and "score" columns
    match_term : str
        String to match (with wildcards)
    fixed_letters : dict
        Fixed letter positions
    length : int
        Length of word
    max_length : int
        Maximum length of word
    min_length : int
        Minimum length of word
    min_score : float
        Minimum score value
    new_to_nyt : bool
        If true, only show entries that have not appeared in NYT
    kwargs
        Passed to Refiner

    Returns
    -------
    pl.DataFrame
        Scored word dataframe with refinement filters applied
    """
    refiner = Refiner(df, **kwargs)
    if match_term:
        refiner =  refiner.match(match_term)
    if length:
        refiner =  refiner.length(length)
    if min_score:
        refiner =  refiner.min_score(min_score)
    if max_length:
        refiner =  refiner.max_length(max_length)
    if min_length:
        refiner =  refiner.min_length(min_length)
    if new_to_nyt:
        refiner = refiner.new_to_nyt_only()

    fixed_letters = fixed_letters or {}
    for k, v in fixed_letters.items():
        refiner =  refiner.fix_letter(k, v)

    return refiner.by_score()
