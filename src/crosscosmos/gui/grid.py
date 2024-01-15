"""
Defines a Grid class, interfacing between the data and gui laters

"""

# Standard library
from enum import Enum
from typing import Tuple, Union

# Third-party
from matplotlib import pyplot as plt
import numpy as np

# Local
import crosscosmos as xc
from crosscosmos.data_models.pydantic_model import Letter, Word


class CellStatus(Enum):
    EMPTY = 0
    SET = 1
    LOCKED = 2
    BLACK = 3


class Cell(object):
    def __init__(self,
                 status: CellStatus = CellStatus.EMPTY,
                 value: str = "",
                 matrix_index: Union[Tuple[int, int], None] = None,
                 gui_coordinates: Union[Tuple[float, float], None] = None
                 ):
        self.status = status
        self.value = value
        self.matrix_index = matrix_index
        self.gui_coordinates = gui_coordinates

    def update(self, value: str):
        if value == " " or value == "":
            self.status = CellStatus.EMPTY
            self.value = ""
        elif value is None:
            self.status = CellStatus.BLACK
            self.value = None
        else:
            self.status = CellStatus.SET
            self.value = value

    def __repr__(self):
        return f"Cell(val='{self.value}', loc={self.matrix_index})"


class Grid(object):

    def __init__(self, grid_size: Tuple[int, int], corpus: xc.corpus.Corpus):

        if grid_size[0] % 2 != 0 or grid_size[1] % 2 != 0:
            raise ValueError("Currently only even numbers are supported for grids")

        self.grid_size = grid_size
        self.row_count = self.grid_size[0]
        self.col_count = self.grid_size[1]

        self.corpus = corpus

        # self.grid = np.full(self.grid_size, ' ', dtype='U1')
        default = [Cell() for _ in range(self.row_count * self.col_count)]
        self.grid = np.full(self.grid_size, None, dtype=object)
        for i in range(self.row_count):
            for j in range(self.col_count):
                self.grid[i, j] = Cell(matrix_index=(i, j))
        self.center = [((self.grid_size[0] - 1) / 2), ((self.grid_size[1] - 1) / 2)]

    def __repr__(self):
        return f"Grid(dim=({self.grid_size[0]}, {self.grid_size[1]})"

    def __getitem__(self, x: Tuple[int, int]) -> str:
        # Check index
        if (x[0] < 0 or x[0] > self.grid_size[0]) or (x[1] < 0 or x[1] > self.grid_size[1]):
            raise IndexError(f"Index outside grid bounds:({self.grid_size[0]}, {self.grid_size[1]})")

        return self.grid[*x]

    def __setitem__(self, x: Tuple[int, int], value: str):
        self.set_grid(x[0], x[1], value)

    def set_grid(self, x: int, y: int, value: str):
        # Check index
        if (x < 0 or x > self.grid_size[0]) or (y < 0 or y > self.grid_size[1]):
            raise IndexError(f"Index outside grid bounds:({self.grid_size[0]}, {self.grid_size[1]})")

        # Check string input
        if isinstance(value, str) and len(value) == 1:
            val = value.upper()
        elif not value:
            val = ''
        else:
            raise IndexError(f"Invalid value: {value}")

        # Set value
        self.grid[x][y].update(val)

        # Set symmetry
        coord_center = self.corner2center(x, y)
        coord_rot_center = -coord_center[0], -coord_center[1]
        cr1, cr2 = self.center2corner(*coord_rot_center)

        if val and not self.grid[cr1][cr2]:
            # If the rotated state is black, then reset that black square to default
            self.grid[cr1][cr2].update("")
        elif not val:
            # Set the rotated state to black
            self.grid[cr1][cr2].update(None)

    def corner2center(self, x: int, y: int) -> Tuple[float, float]:
        """ Convert coordinate measured form corner, to coordinate measured from center of grid

        a: Corner -> Pt         [x,y]
        b: Corner -> Center     self.center
        c: Center -> Pt         [c1,c2]

        a = (b + c)    ->    C = (a - b)
        [c1,c2] = [x,y] - self.center
        """
        return x - self.center[0], y - self.center[1]

    def center2corner(self, c1: float, c2: float) -> Tuple[int, int]:
        """ Convert coordinate measured form center, to coordinate measured from corner

        A: Corner -> Pt         [x,y]
        B: Corner -> Center     self.center
        C: Center -> Pt         [c1,c2]

        A = (B + C)
        self.center + [c1,c2] = [x,y]
        """
        return int(self.center[0] + c1), int(self.center[1] + c2)

    def to_console(self):
        out_str = ""
        for i in range(self.grid_size[0]):
            grid_vals = []
            for x in self.grid[i]:
                match x.status:
                    case CellStatus.EMPTY:
                        gv = "-"
                    case CellStatus.BLACK:
                        gv = "■"
                    j
                if x.status == CellStatus.EMPTY:
                    grid_vals += "-"
                elif not x:
                    grid_vals += "■"
                else:
                    grid_vals += x.value

            out_str += " ".join(grid_vals)

            if i < self.grid_size[0] - 1:
                out_str += "\n"
        print(out_str)


if __name__ == '__main__':
    lc = xc.corpus.Corpus.from_test()
    g = Grid((4, 4), lc)

    x1, x2 = 0, 2
    c1, c2 = g.corner2center(x1, x2)

    g.to_console()

    plt.figure()
    plt.scatter(*g.corner2center(0, 0), c="k")
    plt.scatter(*g.corner2center(0, 4), c="k")
    plt.scatter(*g.corner2center(4, 0), c="k")
    plt.scatter(*g.corner2center(4, 4), c="k")
    plt.scatter(*g.corner2center(0, 2), c="tab:red")
    plt.scatter(-c1, -c2, c="tab:orange")
    plt.grid()
    plt.show(block=False)
