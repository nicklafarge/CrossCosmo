""" Data models for xd word list
"""

# Standard library imports
import logging

# Third-party imports
from pony import orm

# Local imports
import crosscosmos as xc

logger = logging.getLogger(__name__)

# xd database (see crosscosmos/wordlists/parse_xd.py)
xd_word_db_path = xc.crosscosmos_root / "word_dbs" / "xd_words.sqlite"
xd_word_db = orm.Database()
xd_word_db.bind(
    provider="sqlite",
    filename=xd_word_db,
    create_db=True,
)


class XdWord(xd_word_db.Entity):
    word = orm.PrimaryKey(str)
    word_usages = orm.Set("XdWordUsage")


class XdYear(xd_word_db.Entity):
    year = orm.PrimaryKey(int)
    word_usages = orm.Set("XdWordUsage")


class XdPubId(xd_word_db.Entity):
    pubid = orm.PrimaryKey(str)
    word_usages = orm.Set("XdWordUsage")


class XdWordUsage(xd_word_db.Entity):
    id = orm.PrimaryKey(int, auto=True)
    pubid = orm.Required("XdPubId")
    year = orm.Required("XdYear")
    word = orm.Required("XdWord")
    clue = orm.Required(str)


xd_word_db.generate_mapping(create_tables=True)
