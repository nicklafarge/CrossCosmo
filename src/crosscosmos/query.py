
import logging

import polars as pl
from pony import orm

import crosscosmos as xc

logger = logging.getLogger(__name__)


def match(corpus: xc.corpus.Corpus, query: str | xc.grid.CellList):
    return corpus.query(str(query))


def match_by_level(corpus_lvl_dict: dict, query: str, lvl: int = 1):
    if lvl not in corpus_lvl_dict.keys():
        return ValueError(f"Invalid corpus index: {lvl}")

    return match(corpus_lvl_dict[lvl], query)


def query_to_df(query):
    df = pl.DataFrame(w.to_dict() for w in query)
    if len(df) == 0:
        return df

    return df.sort(by="score", descending=True)


def match_words(db, match_str):
    match_str = str(match_str)
    words = orm.select(w for w in db if len(w.word) == len(match_str))
    for i, c in enumerate(match_str):
        if c in xc.constants.PLACEHOLDERS:
            continue
        words = orm.select(w for w in words if w.word[i] == c)
    return query_to_df(words)


def set_df_letter(df: pl.DataFrame, letter_idx: int, value: str):
    assert len(value) == 1
    return df.filter(pl.col("word").str.slice(letter_idx, 1) == value)


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


if __name__ == "__main__":
    logger.info("LOADING")
    corpus_lvls = {
        1: xc.corpus.Corpus.from_test(),
        2: xc.corpus.Corpus.from_diehl(),
        3: xc.corpus.Corpus.from_lafarge(),
        4: xc.corpus.Corpus.from_collab(),
    }

    def m(query: str, lvl: int = 3):
        return match_by_level(corpus_lvls, query, lvl)

    query_str = "A--D"
    test1 = m(corpus_lvls, query_str, 1)
    test2 = m(corpus_lvls, query_str, 2)
    test3 = m(corpus_lvls, query_str, 3)

    # KARANAMOK
    m("------R", 1)
    m("------M-K", 4)
