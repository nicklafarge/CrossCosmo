""" """

import logging

import polars as pl

from crosscosmos.wordlists import LaFargeWord

logger = logging.getLogger("__name__")


def augment_df(df_in: pl.DataFrame) -> pl.DataFrame:
    df = df_in.filter(pl.col("word").str.len_chars() > 2)

    df = df.with_columns(pl.max_horizontal("collab_score", "diehl_score").alias("max_score"))

    return df


def query_to_polars(query_result) -> pl.DataFrame:
    """
    Convert Pony ORM query result to Polars DataFrame.

    Parameters
    ----------
    query_result : pony.orm.core.Query
        Query result from Pony ORM select operation

    Returns
    -------
    pl.DataFrame
        Polars DataFrame containing the query results
    """
    # Convert query result to list of dictionaries
    data = [entity.to_dict() for entity in query_result]

    if not data:
        return pl.DataFrame()

    df = pl.DataFrame(data)
    df = augment_df(df)
    return df.sort(by="max_score", descending=True)


def contains_str_and_removed_str(substr: str, score_threshold=0, filter_start_end: bool = False):
    substr_words = LaFargeWord.select(lambda e: substr in e.word and len(e.word) >= 3 + len(substr))

    keys = ["word", "collab_score", "diehl_score"]

    valid_pairs = []
    for row in substr_words:
        modified_word = row.word.replace(substr, "", 1)
        orig_dict = row.to_dict()

        # Check if the modified word exists in the database
        modified_word_entry = LaFargeWord.get(lambda w: w.word == modified_word)
        if modified_word_entry and len(modified_word_entry.word) > 2:
            entry = {}
            mod_dict = modified_word_entry.to_dict()

            for k in keys:
                entry[f"orig_{k}"] = orig_dict[k]
                entry[f"mod_{k}"] = mod_dict[k]

            valid_pairs.append(entry)

    df = pl.DataFrame(valid_pairs)
    df = df.with_columns(
        [
            (df["orig_collab_score"] + df["mod_collab_score"]).alias("collab_score_sum"),
            (df["orig_diehl_score"] + df["mod_diehl_score"]).alias("diehl_score_sum"),
        ]
    )
    df = df.with_columns([pl.max_horizontal("collab_score_sum", "diehl_score_sum").alias("max_score_sum")])
    df = df.filter(pl.col("max_score_sum") >= score_threshold)

    if filter_start_end:
        df = df.filter((~pl.col("orig_word").str.starts_with(substr)) & (~pl.col("orig_word").str.ends_with(substr)))
    return df.sort(by="max_score_sum", descending=True)
