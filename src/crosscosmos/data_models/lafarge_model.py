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
lafarge_db_path = xc.crosscosmos_root / "word_dbs" / "lafarge_words.sqlite"
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
    clues = orm.Set("LaFargeClue")
    sources = orm.Required(orm.Json)
    collab_score = orm.Optional(int)
    diehl_score = orm.Optional(int)
    xword_link = orm.Optional(str)
    notes = orm.Optional(str)
    is_word = orm.Optional(bool)

    def __repr__(cls):
        return f"LaFargeWord[\'{cls.word}\', {cls.collab_score}]"

    def verbose(cls, override_xword=True):
        if override_xword:
            xword_link = f"https://crosswordtracker.com/answer/{cls.word.lower()}/"
        else:
            xword_link = cls.xword_link
        return f"LaFargeWord[\'{cls.word}\', Collab={cls.collab_score}, Diehl={cls.diehl_score}, xword={xword_link}]"
# class LaFargeWordMeta(type):
#     def __repr__(cls):
#         return f"LaFargeWord[\'{cls.word}\', {cls.collab_score:%i}]"


# def laf_word_repr(w: LaFargeWord) -> str:
#     return


# LaFargeWord.__metaclass__ = LaFargeWordMeta

lafarge_word_db.generate_mapping(create_tables=True)
