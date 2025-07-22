"""Data models for xd word list"""

import logging

import polars as pl
from pony import orm

from crosscosmos.config import project_root

logger = logging.getLogger(__name__)

# xd database (see crosscosmos/wordlists/saul_xd.py)
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
    score = orm.Required(int, default=0)
    clues = orm.Set("LaFargeClue")
    sources = orm.Required(orm.Json)
    collab_score = orm.Optional(int)
    diehl_score = orm.Optional(int)
    xword_link = orm.Optional(str)
    notes = orm.Optional(str)
    is_word = orm.Optional(bool)

    def __repr__(cls):
        return f"LaFargeWord['{cls.word}', {cls.score}]"

    def verbose(cls, override_xword=True):
        if override_xword:
            xword_link = f"https://crosswordtracker.com/answer/{cls.word.lower()}/"
        else:
            xword_link = cls.xword_link
        return f"LaFargeWord['{cls.word}', Collab={cls.collab_score}, Diehl={cls.diehl_score}, xword={xword_link}]"


# class LaFargeWordMeta(type):
#     def __repr__(cls):
#         return f"LaFargeWord[\'{cls.word}\', {cls.collab_score:%i}]"


# def laf_word_repr(w: LaFargeWord) -> str:
#     return


# LaFargeWord.__metaclass__ = LaFargeWordMeta

lafarge_word_db.generate_mapping(create_tables=True)


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


if __name__ == "__main__":
    orm.commit()
    for row in LaFargeWord.select():
        ds = row.diehl_score if row.diehl_score is not None else 0
        cs = row.collab_score if row.collab_score is not None else 0
        row.score = max(ds, cs)
    orm.commit()
    # dflib = contains_str_and_removed_str("LIB", 0, filter_start_end=True)
    #
    # # dfit = contains_str_and_removed_str("IT", 100)
    # dfastra = contains_str_and_removed_str("ASTRA", 0)
    # dfastra = dfastra.sort(by="orig_collab_score", descending=True)
    #
    # dfhoc = contains_str_and_removed_str("HOC", 0)

    # df_astra = query_to_polars(LaFargeWord.select(lambda w: "ASTRA" in w.word))
    #
    #
    #
    # words_with_it = LaFargeWord.select(lambda w: "IT" in w.word)
    #
    # # it_words = select(w for w in Word if "IT" in w.word)
    # valid_pairs = []
    # words_with_it = LaFargeWord.select(lambda w: "IT" in w.word)
    #
    # rmwords = [
    #     wit
    #     for wit in words_with_it
    #     if len(list(LaFargeWord.select(lambda w: w.word == wit.word.replace("IT", "")))) > 0
    # ]
    # # rmwords_good = [w for w in rmwords if ]
    #
    #
    # no_it_words = {
    #     "wit": [],
    #     "noit": [],
    #     "wit_collab_score": [],
    #     "nowit_collab_score": []
    # }
    # for wit in words_with_it:
    #     remove_it = wit.word.replace("IT", "")
    #     remove_it_entries = list(LaFargeWord.select(lambda w: w.word == remove_it))
    #     if len(remove_it_entries) > 0:
    #         rm_word = remove_it_entries[0]
    #         no_it_words["wit"].append(wit.word)
    #         no_it_words["noit"].append(rm_word.word)
    #         no_it_words["wit_collab_score"].append(wit.collab_score)
    #         no_it_words["nowit_collab_score"].append(rm_word.collab_score)
    #
    #         print(
    #             f"[{str(wit.collab_score):<5}] {wit.word:<22} [{str(rm_word.collab_score):<5}] {rm_word.word}"
    #         )
    #
    # df = pl.DataFrame(no_it_words)
    # df = df.with_columns(
    #     [
    #         (df["wit_collab_score"] + df["nowit_collab_score"]).alias("score_sum"),
    #         pl.max("wit_collab_score", "nowit_collab_score").alias("max_score"),
    #     ]
    # ).sort(by="max_score", descending=True)
    # df = df
    # min_score = 50
    # # it_gt_2 = [w for w in words_with_it if w.word.count("IT") >= 2]
    # # print df
