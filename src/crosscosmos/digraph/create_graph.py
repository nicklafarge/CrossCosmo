# Standard library imports
import logging
from typing import Union

# Third party
import networkx as nx
from matplotlib import pyplot as plt
import pony
from pony.orm import select, raw_sql

# Local
import crosscosmos as xc
from crosscosmos.data_models.pydantic_model import Letter, Word
from crosscosmos.data_models.lafarge_model import lafarge_word_db, LaFargeWord
from crosscosmos.digraph.xgraph import LetterSet

logger = logging.getLogger("create_graph")
logger.setLevel(logging.INFO)

pony.options.CUT_TRACEBACK = False

ls = LetterSet(3)
xg = ls.create_graph()


n_words = 100
l3 = [w for w in LaFargeWord.select() if len(w.word) == 3 and not has_numbers(w.word)]
l3 = sorted(l3, key=lambda w: w.collab_score or 0, reverse=True)
l3_filter = [l for l in l3 if l.collab_score and l.collab_score > 85]

for w in l3_filter:
    pw = Word()

# LaFargeWord.select(lambda c: c.collab_score > 90)
# for w in LaFargeWord.select():
#     if len(w.word) == 3:
#         print(w.word)
