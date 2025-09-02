"""Collaborative word list (aka xwordlist)

Source:
    https://github.com/Crossword-Nexus/collaborative-word-list

Last checked: 08/31/2025

"""

import logging

import polars as pl
from pony import orm

from crosscosmos.config import project_root
from crosscosmos.wordlists.parse_utils import parse_word_score


logger = logging.getLogger(__name__)

collab_word_list_path = project_root / "resources" / "word_lists" / "collab_word_list.csv"
collab_word_list_db_path = project_root / "word_dbs" / "collab_word_list_words.sqlite"

collab_word_list_word_db = orm.Database()
collab_word_list_word_db.bind(
    provider="sqlite",
    filename=str(collab_word_list_db_path),
    create_db=True,
)


class CollabWordListWord(collab_word_list_word_db.Entity):
    word = orm.PrimaryKey(str)
    score = orm.Required(int)


collab_word_list_word_db.generate_mapping(create_tables=True)


def populate():
    parse_word_score(collab_word_list_path, CollabWordListWord, ";")
    orm.commit()

def read_dataframe() -> pl.DataFrame:
    """ Reads the wordlist csv into a polars dataframe
    """
    return pl.read_csv(collab_word_list_path, separator=";", has_header=False, new_columns=["word", "score"])

if __name__ == "__main__":
    # populate()
    cdf = read_dataframe()
