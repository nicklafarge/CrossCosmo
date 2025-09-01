"""Broda List - Trimmed by Diehl

Source (Broda):
    https://peterbroda.me/crosswords/wordlist/

Source (Diehl Trimmed List):
    https://www.facebook.com/groups/1515117638602016/files

"""

import logging

import polars as pl
from pony import orm

from crosscosmos.config import project_root
from crosscosmos.wordlists.parse_utils import parse_word_score

logger = logging.getLogger(__name__)

# ====================================================================================================
# Database Model
# ====================================================================================================

diehl_path = project_root / "resources" / "word_lists" / "broda_trimmed_by_diehl_2020.csv"

# diehl database (see crosscosmos/wordlists/diehl.py)
diehl_db_path = project_root / "word_dbs" / "diehl_words.sqlite"
diehl_word_db = orm.Database()
diehl_word_db.bind(
    provider="sqlite",
    filename=str(diehl_db_path),
    create_db=True,
)


class DiehlWord(diehl_word_db.Entity):
    word = orm.PrimaryKey(str)
    score = orm.Required(int)

    def __repr__(self):
        return f"DiehlWord['{self.word}', {self.score}]"


diehl_word_db.generate_mapping(create_tables=True)

# ====================================================================================================
# Database population functions
# ====================================================================================================

def read_dataframe() -> pl.DataFrame:
    """ Reads the wordlist csv into a polars dataframe
    """
    return pl.read_csv(diehl_path, separator=";", has_header=False, new_columns=["word", "score"])

def populate():
    parse_word_score(diehl_path, DiehlWord, ";")
    orm.commit()


if __name__ == "__main__":
    # populate()
    df = read_dataframe()
