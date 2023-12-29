"""
Source:
    https://xd.saul.pw/data/
"""

# Standard library imports
import csv
import logging
import sys

# Third-party imports

# Local imports
import crosscosmos as xc
from crosscosmos.data_models import xd_model

csv.field_size_limit(sys.maxsize)

logger = logging.getLogger(__name__)

xd_path = xc.crosscosmos_root / 'resources' / 'xd_0_to_2m.tsv'
# xd_path = xc.crosscosmos_root / 'resources' / 'xd_4m_onward.tsv'
i = 0
for row in xc.wordlists.parsing_utils.read_csv_generator(xd_path, "\t"):
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
    word_entry = xd_model.XdWord.get(word=word)
    if not word_entry:
        word_entry = xd_model.XdWord(word=word)

    # Only add a usage entry if we have a clue
    if not fmt_clue:
        continue

    word_usage_info = dict(word=word_entry, clue=fmt_clue)

    if pubid:
        # Create the year/publisher if they don't exist
        pubid_entry = xd_model.XdPubId.get(pubid=pubid)
        if not pubid_entry:
            pubid_entry = xd_model.XdPubId(pubid=pubid)
        word_usage_info['pubid'] = pubid_entry

    if year:
        year_entry = xd_model.XdYear.get(year=year)
        if not year_entry:
            year_entry = xd_model.XdYear(year=year)
        word_usage_info['year'] = year_entry

    # Create a new word entry if the clue is new
    try:
        word_usage_entry = xd_model.XdWordUsage.get(**word_usage_info)
    except:
        print(word_usage_info)
        raise
    if not word_usage_entry:
        xd_model.XdWordUsage(**word_usage_info)

    xd_model.orm.commit()
