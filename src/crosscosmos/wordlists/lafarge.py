"""Populate the LaFarge wordlist model from existing sources"""

import logging
import re
from pathlib import Path
from typing import Any, Callable

import numpy as np
import polars as pl
from pony import orm

from crosscosmos.config import project_root
from crosscosmos.wordlists import (
    collaborative_wordlist,
    crosserville,
    crossword_tracker,
    diehl,
    expanded_names,
    saul_xd,
    spread_the_word,
)

logger = logging.getLogger(__name__)

lafarge_full_csv_path = project_root / "resources" / "word_lists" / "lafarge_full_wordlist.txt"
lafarge_wordscore_csv_path = project_root / "resources" / "word_lists" / "lafarge_wordlist.txt"
nyt_words_path = project_root / "resources" / "word_lists" / "nyt_wordlist.txt"

def setup_database_regexp(db_object):
    """
    Links the python 're' module to the SQLite 'REGEXP' function.

    Call this function ONCE after db.bind() and before you query.
    """
    if db_object.provider.dialect != "SQLite":
        return  # This function is only for SQLite

    @db_object.provider.dbapi_connection.create_function("REGEXP", 2)
    def regexp(expr, item):
        if item is None:
            return False
        return re.search(expr, item) is not None

# ====================================================================================================
# Database Model
# ====================================================================================================

lafarge_db_path = project_root / "word_dbs" / "lafarge_words.sqlite"
lafarge_word_db = orm.Database()
lafarge_word_db.bind(
    provider="sqlite",
    filename=str(lafarge_db_path),
    create_db=True,
)


class LaFargeClue(lafarge_word_db.Entity):
    clue: str = orm.Required(str)
    source: str = orm.Optional(str)  # nyt, wsj, etc.
    year: int = orm.Optional(int)
    word = orm.Required("LaFargeWord")


class LaFargeWord(lafarge_word_db.Entity):
    word = orm.PrimaryKey(str)
    score = orm.Required(float, default=0)
    clues = orm.Set("LaFargeClue")
    sources = orm.Required(orm.Json) # 'manual' for ones I put in
    collab_score = orm.Optional(int)
    expname_score = orm.Optional(float)
    diehl_score = orm.Optional(int)
    stw_score = orm.Optional(int)
    xword_link = orm.Optional(str)
    notes = orm.Optional(str)
    is_word = orm.Optional(bool)
    length = orm.Required(int)

    def __repr__(cls):
        return f"LaFargeWord['{cls.word}', {cls.score}]"

    @classmethod
    def add_word(cls, word: str, score: int, **kwargs):
        existing_entry = LaFargeWord.get(word=word)
        if existing_entry:
            raise ValueError(f"Already exists in database: {existing_entry}")

        kwargs.setdefault("sources", ["manual"])
        LaFargeWord(word=word, score=score, **kwargs)
        orm.commit()

    @classmethod
    def remove_word(cls, word: str):
        existing_entry = LaFargeWord.get(word=word)
        if existing_entry:
            existing_entry.delete()
        orm.commit()

    @property
    def avg_score(self):
        # scores_to_average = [
        #     s for s in [self.diehl_score, self.collab_score, self.stw_score, self.expname_score] if s is not None
        # ]
        scores_to_average = [
            s for s in [self.diehl_score, self.collab_score, self.stw_score, self.expname_score]
            if s is not None
        ]
        if scores_to_average:
            return np.mean(scores_to_average)
        else:
            return 0

    @property
    def length(self):
        return len(self.word)

    def verbose(self, override_xword=True):
        if override_xword:
            xword_link = f"https://crosswordtracker.com/answer/{self.word.lower()}/"
        else:
            xword_link = self.xword_link
        return (f"LaFargeWord['{self.word}', "
                f"Collab={self.collab_score}, "
                f"Diehl={self.diehl_score}, "
                f"Stw={self.stw_score}, "
                f"xword={xword_link}]")


# setup_database_regexp(lafarge_word_db)
lafarge_word_db.generate_mapping(create_tables=True)

# ====================================================================================================
# Database population functions
# ====================================================================================================

def update_from_source(
    source_model, source_name: str, update_fn: Callable[[Any, Any], None], batch_size: int = 2000
) -> None:
    """
    Update LaFarge database from a source word list.

    Parameters
    ----------
    source_model : Type[orm.Entity]
        Source database model class
    source_name : str
        Name identifier for the source
    update_fn : Callable
        Function to update LaFargeWord from source word
    batch_size : int
        Records to process before progress update
    """
    logger.info(f"Updating from {source_name}")

    with orm.db_session:
        words = source_model.select()
        total_words = words.count()

        for i, source_word in enumerate(words):
            if i % batch_size == 0:
                logger.info(f"{source_name}: {i / total_words * 100:.1f}%")
                orm.commit()

            # Extract word string
            word_str = source_word.word
            if hasattr(word_str, "word"):  # Handle nested word objects
                word_str = word_str.word

            word_str = word_str.upper().strip()
            if not word_str.isalpha():
                continue

            # Get or create LaFarge word
            laf_word = LaFargeWord.get(word=word_str)
            if laf_word:
                if source_name not in laf_word.sources:
                    laf_word.sources.append(source_name)
            else:
                laf_word = LaFargeWord(word=word_str, sources=[source_name])
                update_fn(laf_word, source_word)
                print(f"New: {laf_word}")

            # Apply source-specific updates
            update_fn(laf_word, source_word)

        orm.commit()
        logger.info(f"Completed updating from {source_name}")

    orm.commit()


def _update_from_xd(laf_word, xd_word: saul_xd.XdWord) -> None:
    """Update LaFarge word with clues from XD dataset."""

    # Get all clues for this word
    xd_usages = saul_xd.XdWordUsage.select(lambda u: u.word == xd_word)

    for usage in xd_usages:
        # Check if clue already exists
        existing_clue = LaFargeClue.get(word=laf_word, clue=usage.clue)

        if not existing_clue:
            LaFargeClue(
                clue=usage.clue,
                source=usage.pubid.pubid if usage.pubid else None,
                year=usage.year.year if usage.year else None,
                word=laf_word,
            )

def populate() -> None:
    """Populate LaFarge database from all sources."""
    # Update from collaborative word list
    update_from_source(
        collaborative_wordlist.CollabWordListWord, "collab_word_list", lambda laf, src: setattr(laf, "collab_score", src.score)
    )

    # Update from Diehl's list
    update_from_source(diehl.XwordWord, "diehl", lambda laf, src: setattr(laf, "diehl_score", src.score))

    # Update from crossword tracker
    update_from_source(crossword_tracker.XwordWord, "xword_tracker", lambda laf, src: setattr(laf, "xword_link", src.info))

    # Update from XD dataset
    update_from_source(saul_xd.XdWord, "xd", _update_from_xd)

    # Update from spread the word
    update_from_source(spread_the_word.XdWord, "spread_the_word", lambda laf, src: setattr(laf, "stw_score", src.score))

    # Update from expanded names
    update_from_source(expanded_names.ExpNameWord, "exp_name", lambda laf, src: setattr(laf, "expname_score", src.score))

    orm.commit()

def update_score():
    for w in LaFargeWord.select():
        w.score = w.avg_score
        w.length = len(w.word)
    orm.commit()


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
    df_collab = collaborative_wordlist.read_dataframe()
    df_crosserville = crosserville.read_dataframe()
    df_diehl = diehl.read_dataframe()
    df_expnames = expanded_names.read_dataframe()
    df_stw = spread_the_word.read_dataframe()

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
    df.write_csv(lafarge_full_csv_path, separator=";")

    df_wordscore = df["word", "score"]
    df_wordscore.write_csv(lafarge_wordscore_csv_path, separator=";")

def read_dataframe(word_score_only: bool = False) -> pl.DataFrame:
    if word_score_only:
        return pl.read_csv(source=lafarge_wordscore_csv_path, separator=";")

    df = pl.read_csv(source=lafarge_full_csv_path, separator=";")
    score_cols = [col for col in df.columns if col.startswith("score_")]

    # Extract the suffix after "score_" for each column
    score_names = [col.replace("score_", "") for col in score_cols]

    # Create expressions that return the score name if the value is not null
    expressions = [
        pl.when(pl.col(col).is_not_null()).then(pl.lit(name)).otherwise(None)
        for col, name in zip(score_cols, score_names, strict=False)
    ]

    return df.with_columns(source=pl.concat_list(expressions).list.drop_nulls())

if __name__ == "__main__":
    # create_csvs()
    df = read_dataframe()
    df_ws = read_dataframe(word_score_only=True)

    # df = from_dataframes()
    df_q4 = df.filter(pl.col("score")>=80)
    df_q3 = df.filter(pl.col("score")>=60)
    df_q2 = df.filter(pl.col("score")>=40)
    df_q1 = df.filter(pl.col("score")>=20)

    df_15 = df_q2.filter(pl.col("length")==15)
    #
    # # Update from expanded names
    # def update_fn(laf, src):
    #     setattr(laf, "expname_score", src.score)
    # update_from_source(expanded_names.ExpNameWord, "exp_name", update_fn)
    #
    # for w in LaFargeWord.select():
    #     w.score = w.avg_score
    #     # w.length = len(w.word)
    # orm.commit()
    #
    # update_score()
    # # Update from collaborative word list
    # # update_from_source(
    # #     collaborative_wordlist.CollabWordListWord, "collab_word_list", lambda laf, src: setattr(laf, "collab_score", src.score)
    # # )
    #
    # # Update from Diehl's list
    # # update_from_source(
    # #     diehl.XwordWord, "diehl", lambda laf, src: setattr(laf, "diehl_score", src.score)
    # # )
    #
    # # Update from crossword tracker
    # # update_from_source(
    # #     crossword_tracker.XwordWord, "xword_tracker", lambda laf, src: setattr(laf, "xword_link", src.info)
    # # )
    #
    # # Update from XD dataset
    # # update_from_source(saul_xd.XdWord, "xd", _update_from_xd)
    #
    # # Update from spread the word
    # # update_from_source(
    # #     spread_the_word.XdWord, "spread_the_word", lambda laf, src: setattr(laf, "stw_score", src.score)
    # # )
    #
    # # orm.commit()

    df_collab = collaborative_wordlist.read_dataframe()
    df_crosserville = crosserville.read_dataframe()
    df_diehl = diehl.read_dataframe()
    df_expnames = expanded_names.read_dataframe()
    df_stw = spread_the_word.read_dataframe()

    test1 = df.filter(pl.col("word")=="POPTOPCAN")
    test2 = df_stw.filter(pl.col("word")=="POPTOPCAN")


    dfc = (df_collab
           .filter(pl.col("word").str.len_chars()==8)
           .filter(pl.col("score").is_between(90, 100)))
    dfc_4050 = dfc["word"].to_list()

    dfl = df.filter(pl.col("length")==8).filter(pl.col("word").is_in(dfc_4050)).filter(pl.col("n_sources")==1)




    dfq = (df
           .filter(pl.col("word").str.len_chars()==8)
           .filter(pl.col("score").is_between(30, 40)))
    dfc_4050 = dfc["word"].to_list()
