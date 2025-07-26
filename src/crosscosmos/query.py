import logging
import re
import string
from typing import Callable

import polars as pl
from pony import orm

import crosscosmos as xc
from crosscosmos import constants
from crosscosmos.wordlists import LaFargeWord

logger = logging.getLogger(__name__)


def query_to_df(query, filter_fn: Callable | None = None) -> pl.DataFrame:
    """ Converts the result of a pony ORM database query to a polars dataframe

    Parameters
    ----------
    query
        Query to convert
    filter_fn : Callable, optional
        User-defined function to filter the results of the query prior to constructing the dataframe

    Returns
    -------
    pl.DataFrame
        DataFrame containing query results
    """
    if filter_fn:
        df = pl.DataFrame(w.to_dict() for w in query if filter_fn(w))
    else:
        df = pl.DataFrame(w.to_dict() for w in query)

    if len(df) == 0:
        return df

    return df.sort(by="score", descending=True)


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

        if c in xc.constants.PLACEHOLDERS:
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

class Query:
    def __init__(
        self,
        db=LaFargeWord,
        q: int = 1,
        sunday: bool = False,
        default: bool = True,
        alpha_only: bool = True,
        limit: int = 100,
    ):
        """Helper class for building crossword database queries

        Parameters
        ----------
        db : pony model, optional, default=LaFargeWord
            Database to query.
        q : int (0-5), default=1
            Quality level corresponding to the minimum score value, where 0-5 correspond to [0,20,40,60,80,100]
        sunday : bool, optional, default=False
            If true, use an NYT sunday grid as the default (21 instead of 15 max length)
        default : bool, optional, default=True
            If true, apply all default filters
        alpha_only : bool, optional, default=True
            If true, only allow alphabet characters
        limit : int, optional, default=100
            Number of entries to return
        """
        assert q in list(range(6))
        self.db = db
        self._query: orm.core.Query = self._alpha_only_db_query() if alpha_only else self.db.select()
        if default:
            min_score = q * 20
            self.default(
                min_score=min_score, max_len=constants.NYT_REGULAR_SIZE if not sunday else constants.NYT_SUNDAY_SIZE
            )

        self._pattern = None
        self._limit = limit

    @property
    def q(self):
        return self._query

    def default(self, min_len: int = 3, max_len: int = constants.NYT_REGULAR_SIZE, min_score: float = 1) -> "Query":
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

    def to_df(self, order_by_score: bool = True) -> pl.DataFrame:
        """Converts the current query result to a polars dataframe"""
        if order_by_score:
            self.order_by_score()

        if self._pattern:
            compiled_pattern = re.compile(self._pattern)
            def filter_fn(w):
                return compiled_pattern.match(w.word)
        else:
            filter_fn = None

        return query_to_df(self._query.limit(self._limit), filter_fn=filter_fn)

    def submit(self, **kwargs) -> pl.DataFrame:
        """Converts the current query result to a polars dataframe"""
        return self.to_df(**kwargs)

    def df(self, **kwargs) -> pl.DataFrame:
        """Converts the current query result to a polars dataframe"""
        return self.to_df(**kwargs)

    def words(self, alphabetical=True) -> list[str]:
        """ Return the result of the query as a list of words
        """
        words = self.to_df(order_by_score=True)["word"].to_list()
        if alphabetical:
            words = sorted(words)
        return words

    def length(self, word_len: int | tuple[int, int]) -> "Query":
        """Filter to only words of a specified length"""
        if isinstance(word_len, int):
            self._query = orm.select(w for w in self._query if len(w.word) == word_len)
        elif isinstance(word_len, tuple) and len(word_len) == 2:
            self.min_length(word_len[0])
            self.max_length(word_len[1])
        else:
            raise ValueError(f"Unexpected input: {word_len}")
        return self

    def min_length(self, word_len: int) -> "Query":
        """Filter to words greater than or equal to a given length"""
        self._query = orm.select(w for w in self._query if len(w.word) >= word_len)
        return self

    def max_length(self, word_len: int) -> "Query":
        """Filter to words less than or equal to a given length"""
        self._query = orm.select(w for w in self._query if len(w.word) <= word_len)
        return self

    def min_score(self, min_score: float) -> "Query":
        """Filter results to all be above a minimum score value"""
        self._query = orm.select(w for w in self._query if w.score >= min_score)
        return self

    def limit(self, limit: int | None) -> "Query":
        """Limit the number of returned rows to a maximum value"""
        self._limit = limit
        return self

    def fix_letters(self, idx: int, letters:str | list[str]):
        """ Fix an index to be a specific letter
        """
        if idx < 0:
            raise ValueError(f"Index must be positive: {idx}")

        if isinstance(letters, str):
            letters = list(letters)

        for letter in letters:
            if len(letter) != 1:
                raise ValueError("Can only fix a single character")

        self._query = orm.select(w for w in self._query if w.word[idx] in letters)

    def exclude_letters(self, idx: int, letters: str | list[str]):
        """ Exclude letter at a given index an index
        """
        if idx < 0:
            raise ValueError(f"Index must be positive: {idx}")

        if isinstance(letters, str):
            letters = list(letters)
        for l in letters:
            if len(l) != 1:
               raise ValueError("Can only fix a single character")

            self._query = orm.select(w for w in self._query if w.word[idx] != l.upper())

    def order_by_score(self) -> "Query":
        """Sort the results by the "score" column"""
        self._query = self._query.order_by(orm.desc(self.db.score))
        return self

    def match(self, match_str: str) -> "Query":
        """
        Match words against a pattern string with wildcards:
        ? - any single letter
        * - any number of letters (0 or more)
        # - consonant
        @ - vowel

        Supports repetition: ?[4], #[3], @[2]
        """
        match_str = str(match_str).upper()

        # Expand repetition patterns
        match_str = expand_match_pattern(match_str)

        # Handle * wildcard by converting pattern to regex
        if "*" in match_str:
            self._pattern = create_match_regex(match_str)
            return self

        # For fixed-length patterns (no * wildcard)
        self.length(len(match_str))

        for i, c in enumerate(match_str):
            if c in xc.constants.PLACEHOLDERS:
                # Any letter - no additional filtering needed
                continue
            elif c == "#":
                # Consonant
                self._query = orm.select(w for w in self._query if w.word[i] in xc.constants.CONSONANTS)
            elif c == "@":
                # Vowel
                self._query = orm.select(w for w in self._query if w.word[i] in xc.constants.VOWELS)
            else:
                # Exact character match
                self._query = orm.select(w for w in self._query if w.word[i] == c)

        return self

    def _alpha_only_db_query(self) -> "Query":
        """Restrict to alphabet characters only (no numbers or symbols)"""
        return orm.select(w for w in self.db if orm.raw_sql(f"TRIM(w.word, '{string.ascii_letters}') = ''"))


def search(query_str: str, **kwargs) -> pl.DataFrame:
    """Performs a basic search matching a template string a basic search, see Query.match

    Parameters
    ----------
    query_str : str
        Query string, see Query.match for usage
    kwargs : dict
        Passed to Query() constructor

    Returns
    -------
    pl.DataFrame
        Query results
    """
    return xc.Query(**kwargs).match(query_str).submit()


def contains_str_and_removed_str(db, substr: str, score_threshold=0, filter_start_end: bool = False):
    substr_words = db.select(lambda e: substr in e.word and len(e.word) >= 3 + len(substr))

    is_lafarge = hasattr(db, "collab_score")
    has_score = hasattr(db, "score")

    score_keys = []
    sort_score = None
    if is_lafarge:
        score_keys.extend(["collab_score", "diehl_score"])
        sort_score = "collab_score"
    elif has_score:
        score_keys.append("score")
        sort_score = "score"

    all_keys = ["word", *score_keys]

    valid_pairs = []
    for row in substr_words:
        modified_word = row.word.replace(substr, "", 1)
        orig_dict = row.to_dict()

        # Check if the modified word exists in the database
        modified_word_entry = db.get(lambda w: w.word == modified_word)
        if modified_word_entry and len(modified_word_entry.word) > 2:
            entry = {}
            mod_dict = modified_word_entry.to_dict()

            for k in all_keys:
                entry[f"orig_{k}"] = orig_dict[k]
                entry[f"mod_{k}"] = mod_dict[k]

            valid_pairs.append(entry)

    df = pl.DataFrame(valid_pairs)

    for k in score_keys:
        df = df.with_columns(
            [
                (df[f"orig_{k}"] + df[f"mod_{k}"]).alias(f"{k}_sum"),
            ]
        )

    if is_lafarge:
        df = df.with_columns([pl.max_horizontal("collab_score_sum", "diehl_score_sum").alias("max_score_sum")])
        df = df.filter(pl.col("max_score_sum") >= score_threshold)
        df = df.sort(by="max_score_sum", descending=True)
    elif has_score:
        df = df.filter(pl.col("score_sum") >= score_threshold)
        df = df.sort(by="score_sum", descending=True)

    if filter_start_end:
        df = df.filter((~pl.col("orig_word").str.starts_with(substr)) & (~pl.col("orig_word").str.ends_with(substr)))
    return df
