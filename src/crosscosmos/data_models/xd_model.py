"""Data models for xd word list"""

import logging

from pony import orm

import crosscosmos as xc

logger = logging.getLogger(__name__)

# xd database (see crosscosmos/wordlists/parse_xd.py)
xd_word_db_path = xc.crosscosmos_project_root / "word_dbs" / "xd_words.sqlite"
xd_word_db = orm.Database()
xd_word_db.bind(
    provider="sqlite",
    filename=str(xd_word_db_path),
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


if __name__ == "__main__":
    from pony.orm import select

    # Query for entries containing "ITIT" substring
    words_with_itit = list(XdWord.select(lambda w: "ITIT" in w.word))
    words_with_itit = select(w for w in XdWord if "ITIT" in w.word)

    # it_words = select(w for w in Word if "IT" in w.word)
    valid_pairs = []
    words_with_it = XdWord.select(lambda w: "IT" in w.word)
    for wit in words_with_it:
        remove_it = wit.word.replace("IT", "")
        remove_it_entries = list(XdWord.select(lambda w: w.word == remove_it))
        if len(remove_it_entries) > 0:
            print(f"{wit.word:<22} {remove_it_entries[0].word}")
    it_gt_2 = [w for w in words_with_it if w.word.count("IT") >= 2]

    # # Execute the query and get results
    # results = list(words_with_itit)
    #
    # # Alternative using SQL LIKE operator for case-insensitive search
    # words_with_itit_like = select(w for w in XdWord if w.word.like('%ITIT%'))
    # results_like = list(words_with_itit_like)
