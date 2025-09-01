"""Collaborative word list (aka xwordlist)

Source:
    https://github.com/Crossword-Nexus/collaborative-word-list

"""

import logging

import polars as pl
from pony import orm

from crosscosmos.config import project_root
from crosscosmos.wordlists.parse_utils import parse_word_score

logger = logging.getLogger(__name__)

spread_the_wrd_list_path = project_root / "resources" / "word_lists" / "spread_the_word_list.txt"
spread_the_word_list_db_path = project_root / "word_dbs" / "stw_list.sqlite"

spread_the_word_list_word_db = orm.Database()
spread_the_word_list_word_db.bind(
    provider="sqlite",
    filename=str(spread_the_word_list_db_path),
    create_db=True,
)


class StwWord(spread_the_word_list_word_db.Entity):
    word = orm.PrimaryKey(str)
    score = orm.Required(int)

spread_the_word_list_word_db.generate_mapping(create_tables=True)

# ====================================================================================================
# Database population functions
# ====================================================================================================

def read_dataframe() -> pl.DataFrame:
    """ Reads the wordlist csv into a polars dataframe
    """
    return pl.read_csv(spread_the_wrd_list_path,
                       separator=";", 
                       has_header=False, 
                       new_columns=["word", "score"])



def populate():
    parse_word_score(spread_the_wrd_list_path, StwWord, ";", score_multiplier=2)
    orm.commit()


if __name__ == "__main__":
    # populate()
    df = read_dataframe()
    print(df)
