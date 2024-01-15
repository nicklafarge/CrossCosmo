
# Standard library imports
import logging
from typing import Union

# Third-party imports
import networkx as nx

# Local imports
import crosscosmos as xc
from crosscosmos.data_models.pydantic_model import Letter, Word

logger = logging.getLogger(__name__)


class LetterSet(object):

    def __init__(self, n_max_letters: int):
        self.n_max_letters = n_max_letters
        self.n_letters = 26

        self.letter_set_list = self._create_set()

    def __getitem__(self, position):
        if isinstance(position, int):
            return self.letter_set_list[position]
        elif len(position) == 2:
            return self.letter_set_list[self.row_major_idx(*position)]
        else:
            raise ValueError(f"Invalid position input: {position}")

    def __setitem__(self, position, value):
        self.letter_set_list[self.row_major_idx(*position)] = value

    def __repr__(self):
        return f"LetterSet(n_max_letters={self.n_max_letters})"

    def row_major_idx(self, letter_idx: int, letter: Union[str, int]) -> int:
        letter_int = xc.letter_utils.char2int(letter) if isinstance(letter, str) else letter
        return letter_idx * self.n_letters + letter_int

    def _create_set(self):
        letter_set_list = []
        for i in range(self.n_max_letters):
            for j in range(self.n_letters):
                l = Letter(s=xc.letter_utils.int2char(j), i=i, j=j, k=self.row_major_idx(i, j), frozen=True)
                letter_set_list.append(l)

        return letter_set_list

    def print_set(self):
        for i in range(self.n_max_letters):
            row = ' '.join([self[i, j].s for j in range(self.n_letters)])
            logger.info(f"{i}) {row}")

    def create_graph(self):
        xg = nx.DiGraph()
        for l in self.letter_set_list:
            xg.add_node(l)
        return xg
