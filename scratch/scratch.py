

import itertools
import logging

import numpy as np

from crosscosmos.corpus import Corpus
from crosscosmos import letter_utils
# from crosscosmos.data_models.lafarge_model import LaFargeWord

logger = logging.getLogger(__name__)


c = Corpus.from_lafarge()
c4 = c.to_n_letter_corpus(46)
c4_de = c4.subtree("DE")