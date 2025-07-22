"""Data models for crossword tracker"""

import logging

from pony import orm

from crosscosmos.config import project_root

logger = logging.getLogger(__name__)

# Crossword tracker database (see crosscosmos/wordlists/crossword_tracker.py)
xword_tracker_db_path = project_root / "word_dbs" / "crossword_tracker_words.sqlite"
xword_tracker_word_db = orm.Database()
xword_tracker_word_db.bind(
    provider="sqlite",
    filename=str(xword_tracker_db_path),
    create_db=True,
)


class XwordWord(xword_tracker_word_db.Entity):
    word = orm.PrimaryKey(str)
    info = orm.Required(str)


xword_tracker_word_db.generate_mapping(create_tables=True)
