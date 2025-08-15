"""Populate the LaFarge wordlist model from existing sources"""

import logging
import re
from typing import Any, Callable

import numpy as np
from pony import orm

from crosscosmos.config import project_root
from crosscosmos.wordlists.collaborative_wordlist import CollabWordListWord
from crosscosmos.wordlists.crossword_tracker import XwordWord
from crosscosmos.wordlists.diehl import DiehlWord
from crosscosmos.wordlists.saul_xd import XdWord, XdWordUsage
from crosscosmos.wordlists.spread_the_word import StwWord
from crosscosmos.wordlists.expanded_names import ExpNameWord

logger = logging.getLogger(__name__)

def setup_database_regexp(db_object):
    """
    Links the python 're' module to the SQLite 'REGEXP' function.

    Call this function ONCE after db.bind() and before you query.
    """
    if db_object.provider.dialect != "SQLite":
        return  # This function is only for SQLite

    @db_object.provider.dbapi_connection.create_function("REGEXP", 2)
    def regexp(expr, item):
        if item is None:
            return False
        return re.search(expr, item) is not None

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
    score = orm.Required(float, default=0)
    clues = orm.Set("LaFargeClue")
    sources = orm.Required(orm.Json) # 'manual' for ones I put in
    collab_score = orm.Optional(int)
    expname_score = orm.Optional(float)
    diehl_score = orm.Optional(int)
    stw_score = orm.Optional(int)
    xword_link = orm.Optional(str)
    notes = orm.Optional(str)
    is_word = orm.Optional(bool)
    length = orm.Required(int)

    def __repr__(cls):
        return f"LaFargeWord['{cls.word}', {cls.score}]"

    @classmethod
    def add_word(cls, word: str, score: int, **kwargs):
        existing_entry = LaFargeWord.get(word=word)
        if existing_entry:
            raise ValueError(f"Already exists in database: {existing_entry}")

        kwargs.setdefault("sources", ["manual"])
        LaFargeWord(word=word, score=score, **kwargs)
        orm.commit()

    @classmethod
    def remove_word(cls, word: str):
        existing_entry = LaFargeWord.get(word=word)
        if existing_entry:
            existing_entry.delete()
        orm.commit()

    @property
    def avg_score(self):
        # scores_to_average = [
        #     s for s in [self.diehl_score, self.collab_score, self.stw_score, self.expname_score] if s is not None
        # ]
        scores_to_average = [
            s for s in [self.diehl_score, self.collab_score, self.stw_score, self.expname_score]
            if s is not None
        ]
        if scores_to_average:
            return np.mean(scores_to_average)
        else:
            return 0

    @property
    def length(self):
        return len(self.word)

    def verbose(self, override_xword=True):
        if override_xword:
            xword_link = f"https://crosswordtracker.com/answer/{self.word.lower()}/"
        else:
            xword_link = self.xword_link
        return (f"LaFargeWord['{self.word}', "
                f"Collab={self.collab_score}, "
                f"Diehl={self.diehl_score}, "
                f"Stw={self.stw_score}, "
                f"xword={xword_link}]")


# setup_database_regexp(lafarge_word_db)
lafarge_word_db.generate_mapping(create_tables=True)

# ====================================================================================================
# Database population functions
# ====================================================================================================

def update_from_source(
    source_model, source_name: str, update_fn: Callable[[Any, Any], None], batch_size: int = 2000
) -> None:
    """
    Update LaFarge database from a source word list.

    Parameters
    ----------
    source_model : Type[orm.Entity]
        Source database model class
    source_name : str
        Name identifier for the source
    update_fn : Callable
        Function to update LaFargeWord from source word
    batch_size : int
        Records to process before progress update
    """
    logger.info(f"Updating from {source_name}")

    with orm.db_session:
        words = source_model.select()
        total_words = words.count()

        for i, source_word in enumerate(words):
            if i % batch_size == 0:
                logger.info(f"{source_name}: {i / total_words * 100:.1f}%")
                orm.commit()

            # Extract word string
            word_str = source_word.word
            if hasattr(word_str, "word"):  # Handle nested word objects
                word_str = word_str.word

            word_str = word_str.upper().strip()
            if not word_str.isalpha():
                continue

            # Get or create LaFarge word
            laf_word = LaFargeWord.get(word=word_str)
            if laf_word:
                if source_name not in laf_word.sources:
                    laf_word.sources.append(source_name)
            else:
                laf_word = LaFargeWord(word=word_str, sources=[source_name])
                update_fn(laf_word, source_word)
                print(f"New: {laf_word}")

            # Apply source-specific updates
            update_fn(laf_word, source_word)

        orm.commit()
        logger.info(f"Completed updating from {source_name}")

    orm.commit()


def _update_from_xd(laf_word, xd_word: XdWord) -> None:
    """Update LaFarge word with clues from XD dataset."""

    # Get all clues for this word
    xd_usages = XdWordUsage.select(lambda u: u.word == xd_word)

    for usage in xd_usages:
        # Check if clue already exists
        existing_clue = LaFargeClue.get(word=laf_word, clue=usage.clue)

        if not existing_clue:
            LaFargeClue(
                clue=usage.clue,
                source=usage.pubid.pubid if usage.pubid else None,
                year=usage.year.year if usage.year else None,
                word=laf_word,
            )

def populate() -> None:
    """Populate LaFarge database from all sources."""
    # Update from collaborative word list
    update_from_source(
        CollabWordListWord, "collab_word_list", lambda laf, src: setattr(laf, "collab_score", src.score)
    )

    # Update from Diehl's list
    update_from_source(DiehlWord, "diehl", lambda laf, src: setattr(laf, "diehl_score", src.score))

    # Update from crossword tracker
    update_from_source(XwordWord, "xword_tracker", lambda laf, src: setattr(laf, "xword_link", src.info))

    # Update from XD dataset
    update_from_source(XdWord, "xd", _update_from_xd)

    # Update from spread the word
    update_from_source(StwWord, "spread_the_word", lambda laf, src: setattr(laf, "stw_score", src.score))

    # Update from expanded names
    update_from_source(ExpNameWord, "exp_name", lambda laf, src: setattr(laf, "expname_score", src.score))

    orm.commit()

def update_score():
    for w in LaFargeWord.select():
        w.score = w.avg_score
        w.length = len(w.word)
    orm.commit()

def update_score():
    for w in LaFargeWord.select():
        w.score = w.avg_score
    orm.commit()


if __name__ == "__main__":
    pass

    # Update from expanded names
    def update_fn(laf, src):
        setattr(laf, "expname_score", src.score)
    update_from_source(ExpNameWord, "exp_name", update_fn)

    for w in LaFargeWord.select():
        w.score = w.avg_score
        # w.length = len(w.word)
    orm.commit()

    update_score()
    # Update from collaborative word list
    # update_from_source(
    #     CollabWordListWord, "collab_word_list", lambda laf, src: setattr(laf, "collab_score", src.score)
    # )

    # Update from Diehl's list
    # update_from_source(
    #     DiehlWord, "diehl", lambda laf, src: setattr(laf, "diehl_score", src.score)
    # )

    # Update from crossword tracker
    # update_from_source(
    #     XwordWord, "xword_tracker", lambda laf, src: setattr(laf, "xword_link", src.info)
    # )

    # Update from XD dataset
    # update_from_source(XdWord, "xd", _update_from_xd)

    # Update from spread the word
    # update_from_source(
    #     StwWord, "spread_the_word", lambda laf, src: setattr(laf, "stw_score", src.score)
    # )

    # orm.commit()