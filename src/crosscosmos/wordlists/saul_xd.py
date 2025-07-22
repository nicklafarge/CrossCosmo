"""
Source:
    https://xd.saul.pw/data/
"""

import csv
import logging
import sys

from pony import orm

from .parse_utils import read_csv_generator

from crosscosmos.config import project_root

logger = logging.getLogger(__name__)

xd_path = project_root / "resources" / "word_lists" / "xd_0_to_2m.tsv"
xd_word_db_path = project_root / "word_dbs" / "xd_words.sqlite"
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


def populate():
    csv.field_size_limit(sys.maxsize)
    # xd_path = xc.crosscosmos_root / 'resources' / 'xd_4m_onward.tsv'
    i = 0
    for row in read_csv_generator(xd_path, "\t"):
        if i % 100 == 0:
            print(i)
        i += 1

        if not row or len(row) != 4:
            continue

        pubid, year, word, clue = row

        if pubid == "pubid":
            continue

        # If we don't have a word, then why bother?
        if not word:
            continue

        fmt_clue = clue.strip().replace(".", "")
        year = int(year)

        # Create the word if it doesn't exist already
        word_entry = XdWord.get(word=word)
        if not word_entry:
            word_entry = XdWord(word=word)

        # Only add a usage entry if we have a clue
        if not fmt_clue:
            continue

        word_usage_info = dict(word=word_entry, clue=fmt_clue)

        if pubid:
            # Create the year/publisher if they don't exist
            pubid_entry = XdPubId.get(pubid=pubid)
            if not pubid_entry:
                pubid_entry = XdPubId(pubid=pubid)
            word_usage_info["pubid"] = pubid_entry

        if year:
            year_entry = XdYear.get(year=year)
            if not year_entry:
                year_entry = XdYear(year=year)
            word_usage_info["year"] = year_entry

        # Create a new word entry if the clue is new
        try:
            word_usage_entry = XdWordUsage.get(**word_usage_info)
        except:
            print(word_usage_info)
            raise
        if not word_usage_entry:
            XdWordUsage(**word_usage_info)

        orm.commit()


if __name__ == "__main__":
    populate()
