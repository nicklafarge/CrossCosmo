import logging
from itertools import chain

import polars as pl

from crosscosmos import constants, load_xc_wordlist
from crosscosmos.refiner import Refiner

logger = logging.getLogger(__name__)

WORD_SCORE_LIST_TYPE = list[tuple[str, float]]
WORD_INDEX_MAP_TYPE = dict[int, dict[int, dict[str, WORD_SCORE_LIST_TYPE]]]

def initialize_word_index_map(max_len: int) -> WORD_INDEX_MAP_TYPE:
    """Creates an empty nested dictionary mapping word lengths to positions to characters.

    Parameters
    ----------
    max_len : int
        The maximum word length to accommodate in the dictionary structure.

    Returns
    -------
    WORD_INDEX_MAP_TYPE
        A pre-structured nested dictionary ready to be populated.
    """
    word_idx_map = {}
    if max_len:
        for word_len in range(1, max_len + 1):
            word_idx_map[word_len] = {}
            for pos in range(max_len):
                word_idx_map[word_len][pos] = {char: [] for char in constants.ALPHABET}
    return word_idx_map


def create_word_index_map(df: pl.DataFrame) -> WORD_INDEX_MAP_TYPE:
    """Creates a word index map using vectorized Polars operations.

    This method avoids slow row-wise iteration by first transforming the DataFrame
    into a long format where each row represents a single character from a word,
    then performs a group-by operation to aggregate words and scores.

    Parameters
    ----------
    df : pl.DataFrame
        DataFrame containing "word", "score", and "length" columns.

    Returns
    -------
    WORD_INDEX_MAP_TYPE
        A nested dictionary mapping [length][position][char] to a list of (word, score) tuples.
    """
    if df.is_empty():
        return {}

    max_len = df["length"].max()
    word_idx_map = initialize_word_index_map(max_len)

    # Create a long-form DataFrame where each row is a character of a word.
    long_df = (
        df.with_columns(
            position=pl.int_ranges(0, pl.col("length")),
            char=pl.col("word").str.split(by=""),
        )
        .explode(["position", "char"])
        .filter(pl.col("char").is_in(list(constants.ALPHABET)))
    )

    # Group by the keys and aggregate words/scores into separate lists. This is
    # more efficient than aggregating into a list of structs.
    agg_df = long_df.group_by(["length", "position", "char"]).agg([
        pl.col("word").alias("words"),
        pl.col("score").alias("scores")
    ])

    # Iterate over the smaller aggregated DataFrame to build the final map.
    for row in agg_df.iter_rows(named=True):
        length, pos, char = row["length"], row["position"], row["char"]
        # Use the highly efficient built-in zip() to create the tuples.
        word_idx_map[length][pos][char] = list(zip(row["words"], row["scores"]))

    return word_idx_map


def tuples_to_df(word_score_tuples: list[tuple[str, float]]) -> pl.DataFrame:
    """Converts a list of (word, score) tuples to a Polars DataFrame.

    Parameters
    ----------
    word_score_tuples : list[tuple[str, float]]
        A list of tuples, where each tuple contains a word and its score.

    Returns
    -------
    pl.DataFrame
        A Polars DataFrame with "word" and "score" columns. Returns an empty
        DataFrame with the correct schema if the input list is empty.
    """
    return pl.DataFrame(word_score_tuples, schema=["word", "score"]) if word_score_tuples else pl.DataFrame(schema=["word", "score"])


def is_wildcard_matched(word_letter: str, wildcard: str) -> bool:
    """Evaluates if a letter matches a specific character or wildcard pattern.

    This function is case-insensitive and supports the following wildcards:
    - '?' : Matches any single character (placeholder).
    - '#' : Matches any consonant.
    - '@' : Matches any vowel.

    Parameters
    ----------
    word_letter : str
        A single character from the word being checked.
    wildcard : str
        The character or wildcard pattern to match against.

    Returns
    -------
    bool
        True if the `word_letter` matches the `wildcard` condition, False otherwise.

    Raises
    ------
    ValueError
        If the `wildcard` is not a recognized character or pattern.
    """
    wildcard = str(wildcard).upper().strip()
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
        """Filters words based on fixed letter positions, with a fast path for simple queries.

        This method efficiently finds words of a specific length that match the given
        letter constraints. It automatically detects if the query contains only
        standard letters and, if so, uses a highly optimized "fast path" that
        avoids function call overhead. For queries with wildcards ('#', '@'),
        it seamlessly falls back to a more flexible matching function.

        To further enhance performance, it analyzes the query to select the
        smallest possible list of candidate words to iterate through.

        Parameters
        ----------
        word_len : int
            The length of the words to search for.
        letter_location : dict[int, str], optional
            A dictionary mapping zero-based letter positions to a character
            (e.g., 'A') or a wildcard ('#', '@'). If None or empty, all words
            of the specified length are returned.

        Returns
        -------
        pl.DataFrame
            A DataFrame containing the matching words and their associated scores,
            sorted by score in descending order.

        """
        # 1. Handle edge case of no specified letter locations.
        if not letter_location:
            all_words = chain.from_iterable(
                v for pos_dict in self.words[word_len].values() for v in pos_dict.values()
            )
            return tuples_to_df(list(all_words))

        # 2. Determine if we can use the optimized "fast path".
        is_fast_path = all(char in constants.ALPHABET for char in letter_location.values())

        # 3. Find the optimal starting list of words to minimize iteration.
        # We check which letter/position pair in the query corresponds to the
        # smallest pre-indexed list of words.
        # 3. Find the optimal starting list of words to minimize iteration.
        best_idx = -1
        min_list_size = float("inf")
        for idx, char in letter_location.items():
            if char in constants.ALPHABET:
                current_size = len(self.words[word_len][idx][char])

                # SHORT-CIRCUIT: If any required letter position has zero matches,
                # the final result must be empty. We can exit immediately.
                if current_size == 0:
                    return pl.DataFrame({"word": [], "score": []}, schema=["word", "score"])

                if current_size < min_list_size:
                    min_list_size = current_size
                    best_idx = idx

        # 4. Select the initial word list and the remaining filter conditions.
        if best_idx != -1:
            start_char = letter_location[best_idx]
            initial_list = self.words[word_len][best_idx][start_char]
            # All other conditions that still need to be checked.
            other_filters = {k: v for k, v in letter_location.items() if k != best_idx}
        else:
            # Fallback for queries containing only wildcards (e.g., "##@@").
            initial_list = list(chain.from_iterable(
                v for pos_dict in self.words[word_len].values() for v in pos_dict.values()
            ))
            other_filters = letter_location

        if not other_filters:
            return tuples_to_df(initial_list)

        # 5. Execute the query using the appropriate path, building columns directly.
        other_filters_items = other_filters.items()
        words_col: list[str] = []
        scores_col: list[float] = []

        if is_fast_path:
            # FAST PATH: Use direct, inline comparisons for maximum speed.
            for word, score in initial_list:
                if all(word[pos] == char for pos, char in other_filters_items):
                    words_col.append(word)
                    scores_col.append(score)
        else:
            # FLEXIBLE PATH: Use the wildcard matching function for complex queries.
            for word, score in initial_list:
                if all(is_wildcard_matched(word[pos], char) for pos, char in other_filters_items):
                    words_col.append(word)
                    scores_col.append(score)

        # 6. Construct the DataFrame from the prepared columns.
        return pl.DataFrame({"word": words_col, "score": scores_col}, schema=["word", "score"])

    def match(self, query_str: str) -> pl.DataFrame:
        """Query the wordmap based on a match string"""
        filter_idxs = {
            i: v for i, v in enumerate(query_str) if v in list(constants.ALPHABET) + constants.PLACEHOLDERS + ["#", "@"]
        }
        return self.filter_by_letters(len(query_str), filter_idxs)


class Corpus:
    def __init__(self, df: pl.DataFrame | None = None, **kwargs):
        self._df: pl.DataFrame = df

        if self._df is None:
            logger.info("Loading default CrossCosmos wordlist...")
            self._df = load_xc_wordlist(**kwargs)

        logger.info("Creating wordmap representation...")
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

df = load_xc_wordlist()
word_map = WordMap(df)

word_len = 8
def test1():
    return [w for w, s in word_map.words[word_len][0]['A'] if w[2] == "A" and w[6] == "D"]

def test2():
    return word_map.filter_by_letters(
        word_len,
        {0: "A", 2: "A", 6: "D"}
    )

def test3():
    return word_map.filter_by_letters(
        word_len,
        {0: "A", 2: "#", 6: "D"}
    )

def test4():
    return Corpus()

if __name__ == "__main__":
    import timeit
    print(timeit.timeit("test1()", globals=locals(), number=100))
    print(timeit.timeit("test2()", globals=locals(), number=100))
    print(timeit.timeit("test3()", globals=locals(), number=100))

    print(timeit.timeit("test4()", globals=locals(), number=5))

    #
    # corpus = Corpus(min_score=30, max_length=15, min_length=3, alpha_only=True)
    # print(corpus.query("--@AD"))
    # print(corpus.query("?????"))
    # print(corpus.query("H???"))
    #
    # corpus.query("H???").filter(pl.col("score").is_between(20, 30))
    # # corpus.df
