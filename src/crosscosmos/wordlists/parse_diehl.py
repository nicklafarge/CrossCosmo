""" Broda List - Trimmed by Diehl

Source (Broda):
    https://peterbroda.me/crosswords/wordlist/

Source (Diehl Trimmed List):
    https://www.facebook.com/groups/1515117638602016/files

"""

# Standard library imports
import csv
import logging

# Third-party imports

# Local imports
import crosscosmos as xc
from crosscosmos.data_models import diehl_model
from crosscosmos.wordlists import parse_word_score

logger = logging.getLogger(__name__)


diehl_path = xc.crosscosmos_root / 'resources' / 'broda_trimmed_by_diehl_2020.csv'


parse_word_score.parse_word_score(diehl_path,
                                  diehl_model.CollabWordListWord,
                                  ";")

diehl_model.orm.commit()
