
# Standard library imports
import logging
from typing import Union

# Third party
import networkx as nx
from pydantic import (
    BaseModel,
    ConfigDict
)
# Local
import crosscosmos as xc

logger = logging.getLogger("eval_xc")
logger.setLevel(logging.INFO)




ls = LetterSet(3)
xg = ls.create_graph()


# ls.print_set()

# xg = nx.DiGraph()
# n_max_letters = 4
# n_letters = len(alphabet)
# for i in range(n_max_letters):
#     for j in range(n_letters):
#         idx = get_node_idx(i, j)
#         l = Letter(s=alphabet[j], i=i, j=j, k=get_node_idx(i, j))
#         attributes = dict(
#             letter=alphabet[j],
#             count=0,
#             i=i
#         )
#         letter=
#         xg.add_node


def add_word(graph: nx.DiGraph, word: str):
    """Add a word to the graph
    """

    pass

# word = "test"
#
# for i, c in enumerate(word):
#     node_idx = get_node_idx(i, char2int(c))
#     n = xg[node_idx]
