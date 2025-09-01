""" Expanded names wordlist

Source:
    https://sites.google.com/view/expandedcrosswordnamedatabase/home

"""

import logging

import polars as pl
from pony import orm

from crosscosmos.config import project_root
from crosscosmos.wordlists.parse_utils import parse_word_score

logger = logging.getLogger(__name__)

expanded_names_file = project_root / "resources" / "word_lists" / "ExpandedNames_scored.txt"
expanded_names_db_path = project_root / "word_dbs" / "exp_names.sqlite"

expanded_names_db = orm.Database()
expanded_names_db.bind(
    provider="sqlite",
    filename=str(expanded_names_db_path),
    create_db=True,
)


class ExpNameWord(expanded_names_db.Entity):
    word = orm.PrimaryKey(str)
    score = orm.Required(float)

expanded_names_db.generate_mapping(create_tables=True)

# ====================================================================================================
# Database population functions
# ====================================================================================================

def read_dataframe() -> pl.DataFrame:
    """ Reads the wordlist csv into a polars dataframe
    """
    return pl.read_csv(expanded_names_file,  encoding="latin1", separator=";", has_header=False, 
                       new_columns=["word", "score"])


def populate():
    parse_word_score(expanded_names_file, ExpNameWord, ";", score_multiplier=1)
    orm.commit()


if __name__ == "__main__":
    # populate()
    df = read_dataframe()
    print(df)
