"""Populate the LaFarge wordlist model from existing sources"""

import logging

from pony import orm

from .collaborative_wordlist import CollabWordListWord
from .crossword_tracker import XwordWord
from .diehl import DiehlWord
from .saul_xd import XdWord, XdWordUsage

from crosscosmos.config import project_root

logger = logging.getLogger(__file__)

# ====================================================================================================
# Database Model
# ====================================================================================================

lafarge_db_path = project_root / "word_dbs" / "lafarge_words.sqlite"
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
    score = orm.Required(int, default=0)
    clues = orm.Set("LaFargeClue")
    sources = orm.Required(orm.Json)
    collab_score = orm.Optional(int)
    diehl_score = orm.Optional(int)
    xword_link = orm.Optional(str)
    notes = orm.Optional(str)
    is_word = orm.Optional(bool)

    def __repr__(cls):
        return f"LaFargeWord['{cls.word}', {cls.score}]"

    def verbose(cls, override_xword=True):
        if override_xword:
            xword_link = f"https://crosswordtracker.com/answer/{cls.word.lower()}/"
        else:
            xword_link = cls.xword_link
        return f"LaFargeWord['{cls.word}', Collab={cls.collab_score}, Diehl={cls.diehl_score}, xword={xword_link}]"


lafarge_word_db.generate_mapping(create_tables=True)

# ====================================================================================================
# Database population functions
# ====================================================================================================

def update_from(db, src_name: str, update_fn) -> None:
    logger.info(f"updating from {src_name}")
    words = db.select()
    n_rows = words.count()
    i = 0
    for w in db.select():
        if i % 2000 == 0:
            logger.info(f"{i / n_rows * 100:.2f}%")

        i += 1

        if isinstance(w.word, str):
            word_str = w.word
        else:
            word_str = w.word.word
        uppercase_word = word_str.upper().strip()
        laf_word = LaFargeWord.get(word=uppercase_word)
        if laf_word:
            if laf_word.sources:
                if src_name not in laf_word.sources:
                    laf_word.sources.append(src_name)
            else:
                laf_word.sources = [src_name]
        else:
            laf_word = LaFargeWord(word=uppercase_word, sources=[src_name])

        update_fn(laf_word, w)

    orm.commit()


def collab_word_list_update_fn(
    laf_word: LaFargeWord,
    db_word: CollabWordListWord,
):
    laf_word.collab_score = db_word.score


def diehl_update_fn(laf_word: LaFargeWord, db_word: DiehlWord):
    laf_word.diehl_score = db_word.score


def xword_tracker_update_fn(laf_word: LaFargeWord, db_word: XwordWord):
    laf_word.xword_link = db_word.info


def xd_update_fn(laf_word: LaFargeWord, db_word: XdWord):
    # Get all xd clues associated with this entry
    xd_usages = XdWordUsage.select(lambda xdw: xdw.word == db_word)

    # Populate the LaFargeClue table from the xd clues
    for xd_usage in xd_usages:
        laf_clue = LaFargeClue.get(word=laf_word, clue=xd_usage.clue)
        if not laf_clue:
            LaFargeClue(
                clue=db_word.clue,
                source=db_word.pubid.pubid,
                year=db_word.year.year,
                word=laf_word,
            )

def populate():
    update_from(
        db=CollabWordListWord,
        src_name="collab_word_list",
        update_fn=collab_word_list_update_fn,
    )

    update_from(db=DiehlWord, src_name="diehl", update_fn=diehl_update_fn)

    update_from(
        db=XwordWord,
        src_name="xword_tracker",
        update_fn=xword_tracker_update_fn,
    )

    orm.commit()

if __name__ == "__main__":
    populate()
