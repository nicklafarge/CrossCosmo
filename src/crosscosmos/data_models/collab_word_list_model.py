""" Data models for diehl word list
"""

# Standard library imports
import logging

# Third-party imports
from pony import orm

# Local imports
import crosscosmos as xc


logger = logging.getLogger(__name__)

# collaborative-word-list database (see crosscosmos/wordlists/parse_collab_word_list.py)
collab_word_list_db_path = xc.crosscosmos_project_root / "word_dbs" / "collab_word_list_words.sqlite"
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
