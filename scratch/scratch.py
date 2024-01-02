"""
Copyright 2023 The Johns Hopkins University Applied Physics Laboratory LLC (JHU/APL).

All Rights Reserved.
This material may be only be used, modified, or reproduced by or for the U.S. Government
pursuant to the license rights granted under the clauses at DFARS 252.227-7013/7014 or
FAR 52.227-14. For any other permission, please contact the Office of Technology Transfer at JHU/APL.
"""

# Standard library imports
import itertools
import logging

# Third-party imports
import numpy as np

# Local imports
from crosscosmos.corpus import Corpus
from crosscosmos import letter_utils
# from crosscosmos.data_models.lafarge_model import LaFargeWord

logger = logging.getLogger(__name__)


c = Corpus.from_lafarge_db()
c4 = c.to_n_letter_corpus(4)
c4_de = c4.subtree("DE")