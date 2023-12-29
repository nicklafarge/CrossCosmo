""" Populate the LaFarge wordlist model from existing sources
"""

# Standard library imports
import logging

# Third-party imports
import pony.orm

# Local imports
from crosscosmos.data_models import (
    collab_word_list_model,
    diehl_model,
    lafarge_model,
    xd_model,
    xword_tracker_model,
)

logger = logging.getLogger("populate_laf_db")


# Iterate through each list and populate the database


def update_from(db, src_name: str, update_fn) -> None:
    logger.info(f"updating from {src_name}")
    words = db.select()
    n_rows = words.count()
    i = 0
    for w in db.select():

        if i % 2000 == 0:
            logger.info(f"{i/n_rows * 100:.2f}%")

        i += 1

        if isinstance(w.word, str):
            word_str = w.word
        else:
            word_str = w.word.word
        uppercase_word = word_str.upper().strip()
        laf_word = lafarge_model.LaFargeWord.get(word=uppercase_word)
        if laf_word:
            if laf_word.sources:
                if src_name not in laf_word.sources:
                    laf_word.sources.append(src_name)
            else:
                laf_word.sources = [src_name]
        else:
            laf_word = lafarge_model.LaFargeWord(word=uppercase_word, sources=[src_name])

        update_fn(laf_word, w)

    lafarge_model.orm.commit()

def collab_word_list_update_fn(laf_word: lafarge_model.LaFargeWord, db_word: collab_word_list_model.CollabWordListWord):
    laf_word.collab_score = db_word.score


def diehl_update_fn(laf_word: lafarge_model.LaFargeWord, db_word: diehl_model.DiehlWord):
    laf_word.diehl_score = db_word.score


def xword_tracker_update_fn(laf_word: lafarge_model.LaFargeWord, db_word: xword_tracker_model.XwordWord):
    laf_word.xword_link = db_word.info


def xd_update_fn(laf_word: lafarge_model.LaFargeWord, db_word: xd_model.XdWord):
    # Get all xd clues associated with this entry
    xd_usages = xd_model.XdWordUsage.select(lambda xdw: xdw.word == db_word)

    # Populate the LaFargeClue table from the xd clues
    for xd_usage in xd_usages:
        laf_clue = lafarge_model.LaFargeClue.get(word=laf_word, clue=xd_usage.clue)
        if not laf_clue:
            lafarge_model.LaFargeClue(clue=db_word.clue,
                                      source=db_word.pubid.pubid,
                                      year=db_word.year.year,
                                      word=laf_word)


update_from(db=collab_word_list_model.CollabWordListWord,
            src_name="collab_word_list",
            update_fn=collab_word_list_update_fn)

update_from(db=diehl_model.DiehlWord,
            src_name="diehl",
            update_fn=diehl_update_fn)

update_from(db=xword_tracker_model.XwordWord,
            src_name="xword_tracker",
            update_fn=xword_tracker_update_fn)

lafarge_model.orm.commit()
# update_from(db=xd_model.xd_word_db,
#             src_name="xd",
#             update_fn=xd_update_fn)
