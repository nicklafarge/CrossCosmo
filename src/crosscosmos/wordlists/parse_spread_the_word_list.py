"""Collaborative word list (aka xwordlist)

Source:
    https://github.com/Crossword-Nexus/collaborative-word-list

"""

import logging

import crosscosmos as xc
from crosscosmos.data_models import spread_the_word_model
from crosscosmos.wordlists import parse_word_score

logger = logging.getLogger(__name__)

collab_word_list_path = xc.crosscosmos_project_root / "resources" / "word_lists" / "spread_the_word_list.txt"

parse_word_score.parse_word_score(
    collab_word_list_path, spread_the_word_model.SpreadTheWordListWord, ";", score_multiplier=2.0
)

spread_the_word_model.orm.commit()
