""" Data models for crossword tracker
"""

# Standard library imports
import logging

# Third-party imports
from pony import orm

# Local imports
import crosscosmos as xc

logger = logging.getLogger(__name__)

# Crossword tracker database (see crosscosmos/wordlists/scrape_crossword_tracker.py)
xword_tracker_db_path = xc.crosscosmos_root / "word_dbs" / "crossword_tracker_words.sqlite"
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
