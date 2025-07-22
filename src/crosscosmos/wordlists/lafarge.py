"""Populate the LaFarge wordlist model from existing sources"""

import logging
from typing import Any, Callable

from pony import orm

from crosscosmos.wordlists.collaborative_wordlist import CollabWordListWord
from crosscosmos.wordlists.crossword_tracker import XwordWord
from crosscosmos.wordlists.diehl import DiehlWord
from crosscosmos.wordlists.saul_xd import XdWord, XdWordUsage
from crosscosmos.wordlists.spread_the_word import StwWord

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
    stw_score = orm.Optional(int)
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

    orm.commit()


if __name__ == "__main__":

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

    for w in LaFargeWord.select():
        if w.diehl_score:
            w.diehl_score = w.diehl_score * 2

    orm.commit()

    # orm.commit()