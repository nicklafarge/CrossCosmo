""" """

import polars as pl

from crosscosmos import refine
from crosscosmos.config import project_root

WORD_LISTS_FOLDER = project_root / "resources" / "word_lists"

XC_FULL_LIST_PATH = project_root / "resources" / "word_lists" / "xc_full_wordlist.txt"
XC_WORDSCORE_LIST_PATH = project_root / "resources" / "word_lists" / "xc_wordlist.txt"


def load_crosserville_wordlist() -> pl.DataFrame:
    """
    Reads the Crosserville word list csv into a polars dataframe

    Word list is stored in browser cookie. Copy contents of 'crosservilled_download.js' into broswer console
    to download the list.
    """
    crosserville_word_list_path = WORD_LISTS_FOLDER / "crosserville_list.csv"
    df = pl.read_csv(crosserville_word_list_path, columns=["n", "s", "w"])
    df = df.rename({"w": "word", "n": "count"})

    s_min = df["s"].min()
    s_max = df["s"].max()
    s_span = s_max - s_min
    df = df.with_columns(score=((pl.col("s") - s_min) / s_span * 100).round())
    df = df.drop("s")
    return df


def load_collab_wordlist() -> pl.DataFrame:
    """Reads the Collaborative word list (aka xwordlist) csv into a polars dataframe

    List source:
        https://github.com/Crossword-Nexus/collaborative-word-list

    Last checked: 08/31/2025
    """
    collab_word_list_path = WORD_LISTS_FOLDER / "collab_word_list.csv"
    return pl.read_csv(collab_word_list_path, separator=";", has_header=False, new_columns=["word", "score"])


def load_diehl_wordlist() -> pl.DataFrame:
    """Reads the Broda word list (trimmed by Diehl bversion) csv into a polars dataframe

    List source (Broda):
        https://peterbroda.me/crosswords/wordlist/

    List source (Diehl Trimmed List):
        https://www.facebook.com/groups/1515117638602016/files

    Last checked: 08/31/2025
    """

    diehl_word_list_path = WORD_LISTS_FOLDER / "broda_trimmed_by_diehl_2020.csv"
    return pl.read_csv(diehl_word_list_path, separator=";", has_header=False, new_columns=["word", "score"])


def load_expanded_names_wordlist() -> pl.DataFrame:
    """Reads the "expanded names" word list csv into a polars dataframe

    List source:
        https://sites.google.com/view/expandedcrosswordnamedatabase/home

    """
    expanded_names_file = WORD_LISTS_FOLDER / "ExpandedNames_scored.txt"
    return pl.read_csv(expanded_names_file,
                       encoding="latin1",
                       separator=";",
                       has_header=False,
                       new_columns=["word", "score"])

def load_spread_the_word_wordlist() -> pl.DataFrame:
    """Reads the "spread the word" word list csv into a polars dataframe

    Source:
        https://github.com/Crossword-Nexus/collaborative-word-list

    """
    spread_the_word_list_db_path = WORD_LISTS_FOLDER / "spread_the_word_list.txt"
    df = pl.read_csv(spread_the_word_list_db_path,
                       separator=";",
                       has_header=False,
                       new_columns=["word", "score"])
    df = df.with_columns(pl.col("word").str.to_uppercase().alias("word"))
    return df.sort("score", descending=True)


def merge_scored_lists(
    dataframes: dict[str, pl.DataFrame],
    weights: dict[str, float] | float | None = None,
    discounts: dict[str, float] | None = None,
    score_col: str = "score",
    word_col: str = "word",
    nyt_words_file: str | None = None,
) -> pl.DataFrame:
    """
    Merge multiple dataframes and calculate weighted average of scores.

    Processes words by removing accents, converting to uppercase, and filtering
    by length and alphabetic characters. Uses native Polars operations for performance.

    Parameters
    ----------
    dataframes : dict[str, pl.DataFrame]
        Dict mapping names to dataframes, each with word and score columns
    weights : dict[str, float] or float, optional
        Weights for each dataframe's scores
    discounts : dict[str, float], optional
        Discount factors to apply to specific dataframes' scores when they are
        the only source for a word. E.g., {"foo": 0.8} reduces foo's scores by
        20% only for words that appear exclusively in foo's dataframe
    score_col : str, default "score"
        Name of the score column in input dataframes
    word_col : str, default "word"
        Name of the word column to merge on
    nyt_words_file : str, optional
        Path to text file containing NYT words (one per line)

    Returns
    -------
    pl.DataFrame
        Processed dataframe with columns: word, score, length, n_sources,
        in_nyt, individual scores, and sources list
    """
    import unicodedata
    from pathlib import Path

    if not dataframes:
        raise ValueError("At least one dataframe is required")

    df_names = list(dataframes.keys())

    # Normalize weights to dict
    if weights is None:
        weights = {name: 1.0 for name in df_names}
    elif isinstance(weights, (int, float)):
        weights = {name: float(weights) for name in df_names}
    elif not isinstance(weights, dict):
        raise TypeError("Weights must be dict, numeric, or None")

    # Validate discounts
    if discounts is None:
        discounts = {}
    elif not isinstance(discounts, dict):
        raise TypeError("Discounts must be dict or None")

    def remove_accents(text: str) -> str | None:
        """Remove diacritical marks from text."""
        if text is None:
            return None
        nfd = unicodedata.normalize("NFD", text)
        return "".join(char for char in nfd if unicodedata.category(char) != "Mn")

    # Load NYT words if provided
    nyt_words = set()
    if nyt_words_file:
        nyt_path = Path(nyt_words_file)
        if nyt_path.exists():
            with open(nyt_path, "r") as f:
                nyt_words = {line.strip().upper() for line in f if line.strip()}

    # Concatenate all dataframes with metadata
    frames = []
    for name, df in dataframes.items():
        frames.append(
            df.select(
                [
                    pl.col(word_col),
                    # Don't apply discount here - will apply conditionally later
                    pl.col(score_col).cast(pl.Float64),
                    pl.lit(name).alias("source"),
                    pl.lit(weights.get(name, 1.0), dtype=pl.Float64).alias("weight"),
                ]
            )
        )

    combined = pl.concat(frames)

    # Process words: remove accents, uppercase, filter
    combined = combined.with_columns(
        [pl.col(word_col).map_elements(remove_accents, return_dtype=pl.Utf8).str.to_uppercase()]
    ).filter(
        pl.col(word_col).str.contains("^[A-Z]+$")  # Only alphabetic
        & pl.col(word_col).str.len_chars().is_between(3, 21)  # Length 3-21
    )

    # Group by word and aggregate
    result = (
        combined.group_by(word_col)
        .agg(
            [
                # Weighted sum components
                (pl.col(score_col) * pl.col("weight")).sum().alias("_weighted_sum"),
                pl.col("weight").sum().alias("_total_weight"),
                # Individual scores per source (raw, undiscounted)
                *[
                    pl.when(pl.col("source") == name)
                    .then(pl.col(score_col))
                    .max()  # Max captures the single non-null value per group
                    .alias(f"score_{name}")
                    for name in df_names
                ],
                # Sources list
                pl.col("source").unique().sort().alias("sources"),
            ]
        )
        .with_columns(
            [
                # Count sources for conditional discount logic
                pl.col("sources").list.len().alias("n_sources")
            ]
        )
        .with_columns(
            [
                # Calculate weighted average with conditional discount
                pl.when(pl.col("n_sources") == 1)
                .then(
                    # Single source: apply discount if applicable
                    pl.when(pl.col("sources").list.first().is_in(list(discounts.keys())))
                    .then(
                        pl.col("_weighted_sum")
                        / pl.col("_total_weight")
                        * pl.col("sources")
                        .list.first()
                        .map_elements(lambda s: discounts.get(s, 1.0), return_dtype=pl.Float64)
                    )
                    .otherwise(pl.col("_weighted_sum") / pl.col("_total_weight"))
                )
                .otherwise(
                    # Multiple sources: no discount
                    pl.col("_weighted_sum") / pl.col("_total_weight")
                )
                .alias(score_col),
                pl.col(word_col).str.len_chars().alias("length"),
                # Check NYT membership
                pl.col(word_col).is_in(list(nyt_words)).alias("in_nyt") if nyt_words else pl.lit(False).alias("in_nyt"),
            ]
        )
        .select(
            [
                # Order columns logically
                pl.col(word_col),
                pl.col(score_col),
                pl.col("length"),
                pl.col("n_sources"),
                pl.col("in_nyt"),
                *[f"score_{name}" for name in df_names],
                pl.col("sources"),
            ]
        )
        .sort(by=["length", score_col], descending=[False, True])
    )

    return result


def from_dataframes():
    """ Creates a combined dataframe populated with data from each of the sources
    """
    nyt_words_path = WORD_LISTS_FOLDER / "nyt_wordlist.txt"

    df_collab = load_collab_wordlist()
    df_crosserville = load_crosserville_wordlist()
    df_diehl = load_diehl_wordlist()
    df_expnames = load_expanded_names_wordlist()
    df_stw = load_spread_the_word_wordlist()

    return merge_scored_lists(
        dataframes={
            "collab": df_collab,
            "crosserville": df_crosserville,
            "diehl": df_diehl,
            "expnames": df_expnames,
            "stw": df_stw,
        },
        weights={"collab": 0.1, "crosserville": 1, "diehl": 1, "expnames": 0.8, "stw": 1},
        discounts={"collab": 0.8},
        nyt_words_file=nyt_words_path
    )

def create_csvs():
    """ Generates the combined DataFrame, and saves it to a file
    """
    df = from_dataframes()
    df = df.drop("sources")
    df.write_csv(XC_FULL_LIST_PATH, separator=";")

    df_wordscore = df["word", "score"]
    df_wordscore.write_csv(XC_WORDSCORE_LIST_PATH, separator=";")

def read_xc_wordlist(word_score_only: bool = False) -> pl.DataFrame:
    """ Load the default CrossCosmos wordlist from a CSV file

    Parameters
    ----------
    word_score_only : bool
        If true, load the csv that contains only the "word" and "score" column

    Returns
    -------
    pl.DataFrame
        Loaded wordlist
    """
    if word_score_only:
        return pl.read_csv(source=XC_WORDSCORE_LIST_PATH, separator=";")

    df = pl.read_csv(source=XC_FULL_LIST_PATH, separator=";")
    score_cols = [col for col in df.columns if col.startswith("score_")]

    # Extract the suffix after "score_" for each column
    score_names = [col.replace("score_", "") for col in score_cols]

    # Create expressions that return the score name if the value is not null
    expressions = [
        pl.when(pl.col(col).is_not_null()).then(pl.lit(name)).otherwise(None)
        for col, name in zip(score_cols, score_names, strict=False)
    ]

    return df.with_columns(source=pl.concat_list(expressions).list.drop_nulls())

def load_xc_wordlist(word_score_only: bool = False, **kwargs) -> pl.DataFrame:
    """ Load the default CrossCosmos wordlist from a CSV file

    Parameters
    ----------
    word_score_only : bool
        If true, load the csv that contains only the "word" and "score" column
    kwargs
        Passed to the 'refine' function

    Returns
    -------
    pl.DataFrame
        Loaded wordlist, refined by kwargs (if specified)
    """
    df = read_xc_wordlist(word_score_only)
    if kwargs:
        return refine(df, **kwargs)
    else:
        return df

if __name__ == "__main__":
    # create_csvs()
    df = load_xc_wordlist(word_score_only=False)
    df_ws = load_xc_wordlist(word_score_only=True)

    df_q3 = load_xc_wordlist(word_score_only=False, q=3, length=15)
    dfz = load_xc_wordlist(word_score_only=False, q=4, length=15, new_to_nyt=True)

