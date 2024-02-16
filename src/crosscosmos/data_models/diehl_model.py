""" Data models for diehl word list
"""

# Standard library imports
import logging

# Third-party imports
from pony import orm

# Local imports
import crosscosmos as xc

logger = logging.getLogger(__name__)

# diehl database (see crosscosmos/wordlists/parse_diehl.py)
diehl_db_path = xc.crosscosmos_project_root / "word_dbs" / "diehl_words.sqlite"
diehl_word_db = orm.Database()
diehl_word_db.bind(
    provider="sqlite",
    filename=str(diehl_db_path),
    create_db=True,
)
# test database
test_db_path = xc.crosscosmos_project_root / "word_dbs" / "test_words.sqlite"
test_word_db = orm.Database()
test_word_db.bind(
    provider="sqlite",
    filename=str(test_db_path),
    create_db=True,
)


class DiehlWord(diehl_word_db.Entity):
    word = orm.PrimaryKey(str)
    score = orm.Required(int)
    
    def __repr__(cls):
        return f"DiehlWord[\'{cls.word}\', {cls.score}]"


diehl_word_db.generate_mapping(create_tables=True)


class TestWord(test_word_db.Entity):
    word = orm.PrimaryKey(str)
    score = orm.Required(int)
    
    def __repr__(cls):
        return f"TestWord[\'{cls.word}\', {cls.score}]"


test_word_db.generate_mapping(create_tables=True)
