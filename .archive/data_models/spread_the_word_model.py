"""Data models for the "spread the word" word list

Source: https://www.spreadthewordlist.com/wordlist
"""

import logging

from pony import orm

from crosscosmos.config import project_root

logger = logging.getLogger(__name__)

# spread the word database (see crosscosmos/wordlists/spread_the_word.py)
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


spread_the_word_list_word_db.generate_mapping(create_tables=True)
