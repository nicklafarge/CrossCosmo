from typing import Callable
import logging
import re
import string

import polars as pl
from pony import orm

import crosscosmos as xc
from crosscosmos import constants
from crosscosmos.wordlists import LaFargeWord

logger = logging.getLogger(__name__)


def query_to_df(query, filter_fn: Callable | None = None):
    if not filter_fn:
        def filter_fn(w):
            return True
    df = pl.DataFrame(w.to_dict() for w in query if filter_fn(w))
    if len(df) == 0:
        return df

    return df.sort(by="score", descending=True)

def _expand_pattern(pattern):
    """
    Expand pattern with repetition syntax into full pattern.
    Examples: ?[4] -> ????, #[3] -> ###
    """
    # Match repetition patterns like ?[4], #[3], @[2]
    repetition_pattern = r"([?#@])(\[(\d+)\])"

    def replacer(match):
        char = match.group(1)
        count = int(match.group(3))
        return char * count

    return re.sub(repetition_pattern, replacer, pattern)


def match_words(db, match_str):
    """Finds words by matching a custom pattern against the database.

    This function translates a custom pattern string into a regular expression
    to perform an efficient query against a SQLite database. It requires
    a user-defined REGEXP function to be registered with the connection.

    Parameters
    ----------
    db : pony.orm.Database
        The Pony ORM database object, which must be connected and
        contain the `Word` entity.
    match_str : str
        The custom pattern string used for matching.

    Returns
    -------
    list[str]
        A list of words from the database that match the provided pattern.

    Notes
    -----
    The matching logic supports several custom placeholders and a repetition syntax.

    **Placeholders:**
    - `?` : any single letter
    - `*` : any number of characters (zero or more)
    - `#` : any consonant
    - `@` : any vowel
    - `&` : any digit [0-9]

    **Repetition:**
    The `c[n]` syntax repeats the character `c` exactly `n` times. The character `c`
    can be a literal letter or any of the placeholders above.

    Examples
    --------
    >>> # Assuming a database `db` is set up with relevant words.
    >>> match_words(db, 'h@?p')
    ['help', 'hope']

    >>> match_words(db, 'c*t')
    ['cat', 'cost', 'constitute']

    >>> match_words(db, 'bo[2]k')
    ['book']

    >>> match_words(db, 'plan&')
    ['plan9']

    >>> match_words(db, '#[3]le')
    ['triple']
    """
    # Expand repetition patterns like o[2] -> oo or #[3] -> ###
    expanded_str = re.sub(r'(.)\[(\d+)\]', lambda m: m.group(1) * int(m.group(2)), str(match_str))

    # Translate the custom pattern into a regex pattern string
    regex_pattern = ""
    for char in expanded_str:
        if char == '?': regex_pattern += '[a-zA-Z]'
        elif char == '*': regex_pattern += '.*'
        elif char == '#': regex_pattern += f'[{constants.CONSONANTS}]'
        elif char == '@': regex_pattern += f'[{constants.VOWELS}]'
        elif char == '&': regex_pattern += '[0-9]'
        elif char in ".+^${}()|[]\\": regex_pattern += '\\' + char
        else: regex_pattern += char

    # Anchor the regex and escape it for safe use in an SQL string
    full_regex = f"^{regex_pattern}$"
    safe_regex_for_sql = full_regex.replace("'", "''")

    # Build the final SQL query string explicitly
    sql_query = f"SELECT word FROM Word WHERE word REGEXP '{safe_regex_for_sql}'"

    # Execute the raw SQL query
    results = db.select(sql_query)

    return list(results)


class Query:
    def __init__(self,
                 db=LaFargeWord,
                 q: int = 1,
                 sunday: bool = False,
                 default: bool = True,
                 alpha_only: bool = True,
                 limit: int = 100):
        """ Helper class for building crossword database queries

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
                min_score=min_score,
                max_len=constants.NYT_REGULAR_SIZE if not sunday else constants.NYT_SUNDAY_SIZE
            )

        self._pattern = None
        self._limit = limit

    @property
    def q(self):
        return self._query

    def default(self, min_len: int = 3, max_len: int = constants.NYT_REGULAR_SIZE, min_score: float = 1) -> "Query":
        """ Sets default query parameters:

        Defaults:
            - Only alphabet entries
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
        """ Converts the current query result to a polars dataframe
        """
        if order_by_score:
            self.order_by_score()

        if self._pattern:
            def filter_fn(w):
                return self._pattern.match(w.word)
        else:
            filter_fn = None

        return query_to_df(self._query.limit(self._limit), filter_fn=filter_fn)

    def submit(self, **kwargs) -> pl.DataFrame:
        """ Converts the current query result to a polars dataframe
        """
        return self.to_df(**kwargs)

    def df(self, **kwargs) -> pl.DataFrame:
        """ Converts the current query result to a polars dataframe
        """
        return self.to_df(**kwargs)

    def length(self, word_len: int | tuple[int, int]) -> "Query":
        """ Filter to only words of a specified length
        """
        if isinstance(word_len, int):
            self._query = orm.select(w for w in self._query if len(w.word) == word_len)
        elif isinstance(word_len, tuple) and len(word_len) == 2:
            self.min_length(word_len[0])
            self.max_length(word_len[1])
        else:
            raise ValueError(f"Unexpected input: {word_len}")
        return self

    def min_length(self, word_len: int) -> "Query":
        """ Filter to words greater than or equal to a given length
        """
        self._query = orm.select(w for w in self._query if len(w.word) >= word_len)
        return self

    def max_length(self, word_len: int) -> "Query":
        """ Filter to words less than or equal to a given length
        """
        self._query = orm.select(w for w in self._query if len(w.word) <= word_len)
        return self

    # def match(self, match_str: str) -> "Query":
    #     """ Find entries in a database given a match string, allowing for optional placeholders for unconstrainted
    #     characters ('?', '-', and ' ')
    #     """
    #     match_str = str(match_str)
    #     self.length(len(match_str))
    #     for i, c in enumerate(match_str):
    #         if c in xc.constants.PLACEHOLDERS:
    #             continue
    #         self._query = orm.select(w for w in self._query if w.word[i] == c)
    #     return self

    def min_score(self, min_score: float) -> "Query":
        """ Filter results to all be above a minimum score value
        """
        self._query = orm.select(w for w in self._query if w.score >= min_score)
        return self

    def limit(self, limit: int) -> "Query":
        """ Limit the number of returned rows to a maximum value
        """
        self._limit = limit
        return self

    def order_by_score(self) -> "Query":
        """ Sort the results by the "score" column
        """
        self._query = self._query.order_by(orm.desc(self.db.score))
        return self

    def match(self, match_str) -> "Query":
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
        match_str = _expand_pattern(match_str)

        # Handle * wildcard by converting pattern to regex
        if "*" in match_str:
            return self.match_words_regex(match_str)

        # For fixed-length patterns (no * wildcard)
        self.length(len(match_str))

        for i, c in enumerate(match_str):
            if c == "?":
                # Any letter - no additional filtering needed
                continue
            elif c == "#":
                # Consonant
                words = orm.select(w for w in self._query if w.word[i] in xc.constants.CONSONANTS)
            elif c == "@":
                # Vowel
                words = orm.select(w for w in self._query if w.word[i] in xc.constants.VOWELS)
            elif c in xc.constants.PLACEHOLDERS:
                # Handle any existing placeholders
                continue
            else:
                # Exact character match
                words = orm.select(w for w in self._query if w.word[i] == c)

        return self

    def match_words_regex(self, match_str) -> "Query":
        """
        Handle patterns with * wildcard using regex.
        """
        # Build regex pattern
        regex_parts = []
        i = 0

        while i < len(match_str):
            c = match_str[i]

            if c == "?":
                regex_parts.append("[a-zA-Z]")
            elif c == "*":
                regex_parts.append("[a-zA-Z]*")
            elif c == "#":
                regex_parts.append("[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]")
            elif c == "@":
                regex_parts.append("[aeiouAEIOU]")
            elif c in xc.constants.PLACEHOLDERS:
                regex_parts.append("[a-zA-Z]")  # Treat as any letter
            else:
                regex_parts.append(re.escape(c))

            i += 1

        regex_pattern = "^" + "".join(regex_parts) + "$"
        self._pattern = re.compile(regex_pattern)
        return self


    def _alpha_only_db_query(self) -> "Query":
        """ Restrict to alphabet characters only (no numbers or symbols
        """
        return orm.select(
            w for w in self.db if orm.raw_sql(f"TRIM(w.word, '{string.ascii_letters}') = ''")
        )


def search(query_str: str, **kwargs) -> pl.DataFrame:
    """ Performs a basic search matching a template string a basic search, see Query.match

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

    all_keys = ["word"] + score_keys

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

