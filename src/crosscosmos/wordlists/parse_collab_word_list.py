""" Collaborative word list (aka xwordlist)

Source:
    https://github.com/Crossword-Nexus/collaborative-word-list

"""

# Standard library imports
import logging

# Third-party imports

# Local imports
import crosscosmos as xc
from crosscosmos.data_models import collab_word_list_model
from crosscosmos.wordlists import parse_word_score

logger = logging.getLogger(__name__)

collab_word_list_path = xc.crosscosmos_project_root / 'resources' / 'collab_word_list.csv'

parse_word_score.parse_word_score(collab_word_list_path,
                                  collab_word_list_model.CollabWordListWord,
                                  ";")

collab_word_list_model.orm.commit()
