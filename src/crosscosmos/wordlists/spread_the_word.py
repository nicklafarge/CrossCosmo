"""Collaborative word list (aka xwordlist)

Source:
    https://github.com/Crossword-Nexus/collaborative-word-list

"""

import logging

from pony import orm

from .parse_utils import parse_word_score

from crosscosmos.config import project_root

logger = logging.getLogger(__name__)

collab_word_list_path = project_root / "resources" / "word_lists" / "spread_the_word_list.txt"
spread_the_word_list_db_path = project_root / "word_dbs" / "spread_the_word_list_words.sqlite"

spread_the_word_list_word_db = orm.Database()
spread_the_word_list_word_db.bind(
    provider="sqlite",
    filename=str(spread_the_word_list_db_path),
    create_db=True,
)


class SpreadTheWordListWord(spread_the_word_list_word_db.Entity):
    word = orm.PrimaryKey(str)
    score = orm.Required(int)


def populate():
    parse_word_score(collab_word_list_path, SpreadTheWordListWord, ";", score_multiplier=2)
    orm.commit()


if __name__ == "__main__":
    populate()
