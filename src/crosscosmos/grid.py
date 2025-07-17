"""
Defines a Grid class, interfacing between the data and gui laters

"""

# Standard library
import copy
from enum import Enum
import random
import string
from typing import Tuple, Union, List
from pathlib import Path

# Third-party
import logging
import numpy as np

# Local
import crosscosmos as xc

logger = logging.getLogger(__name__)


class CellStatus(Enum):
    EMPTY = 0
    SET = 1
    LOCKED = 2
    BLACK = 3


class GridDirection(Enum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3


class WordDirection(Enum):
    HORIZONTAL = 1
    VERTICAL = 2

    @staticmethod
    def flip(cls):
        match cls:
            case WordDirection.HORIZONTAL:
                return WordDirection.VERTICAL
            case WordDirection.VERTICAL:
                return WordDirection.HORIZONTAL
            case _:
                raise ValueError("invalid word direction")


class GridSymmetry(Enum):
    NONE = 0
    ROTATIONAL = 1
    REFLECTION = 2


class MoveDirection(Enum):
    FORWARD_HORIZONTAL = 1
    FORWARD_VERTICAL = 2
    BACK_HORIZONTAL = 3
    BACK_VERTICAL = 4


class GridStatus(Enum):
    COMPLETE = 1
    INCOMPLETE = 2
    INVALID = 3


class Cell(object):
    def __init__(self,
                 x: int, y: int,
                 status: CellStatus = CellStatus.EMPTY,
                 value: str = "",
                 gui_coordinates: Union[Tuple[float, float], None] = None,
                 shuffle=True):
        self.status = status
        self.value = value
        self.matrix_index = (x, y)
        self.x = x
        self.y = y
        self.gui_coordinates = gui_coordinates
        self.gui_row = None
        self.gui_col = None

        self.is_h_start = False
        self.is_h_end = False
        self.is_v_start = False
        self.is_v_end = False
        self.answer_number = None

        self.hlen = 0
        self.vlen = 0

        # Keep track of any word that have been removed from consideration due to this cell
        self.removed_words = []
        self.excluded = []

        self.queue_order = list(reversed(string.ascii_uppercase))
        # self.queue = list(string.ascii_uppercase)

        self.queue = copy.deepcopy(self.queue_order)
        if shuffle:
            random.shuffle(self.queue)

    def __repr__(self):
        return f"Cell(val='{self.value}', loc={self.matrix_index})"

    def to_json(self):
        return {
            'status': self.status.value,
            'value': self.value,
            'matrix_index': self.matrix_index,
            'x': self.x,
            'y': self.y,
            'gui_coordinates': self.gui_coordinates,
            'gui_row': self.gui_row,
            'gui_col': self.gui_col,
            'is_h_start': self.is_h_start,
            'is_h_end': self.is_h_end,
            'is_v_start': self.is_v_start,
            'is_v_end': self.is_v_end,
            'answer_number': self.answer_number,
            'hlen': self.hlen,
            'vlen': self.vlen,
        }

    @classmethod
    def from_dict(cls, json_cell: dict):
        cell = cls(x=json_cell['x'],
                   y=json_cell['y'],
                   status=CellStatus(json_cell['status']),
                   value=json_cell['value'],
                   gui_coordinates=json_cell['gui_coordinates'])
        cell.matrix_index = json_cell['matrix_index']
        cell.gui_row = json_cell['gui_row']
        cell.gui_col = json_cell['gui_col']
        cell.is_h_start = json_cell['is_h_start']
        cell.is_h_end = json_cell['is_h_end']
        cell.is_v_start = json_cell['is_v_start']
        cell.is_v_end = json_cell['is_v_end']
        cell.answer_number = json_cell['answer_number']
        cell.hlen = json_cell['hlen']
        cell.vlen = json_cell['vlen']
        return cell

    @classmethod
    def load(cls, filename: Path, **kwargs):
        return cls.from_dict(xc.io_utils.load_json(filename), **kwargs)

    @property
    def is_valid(self):
        return self.status == CellStatus.BLACK or (self.hlen >= 3 and self.vlen >= 3)

    def is_start(self, direction=WordDirection):
        match direction:
            case WordDirection.HORIZONTAL:
                return self.is_h_start
            case WordDirection.VERTICAL:
                return self.is_v_start
            case _:
                raise ValueError("Invalid WordDirection")

    def is_end(self, direction=WordDirection):
        match direction:
            case WordDirection.HORIZONTAL:
                return self.is_h_end
            case WordDirection.VERTICAL:
                return self.is_v_end
            case _:
                raise ValueError("Invalid WordDirection")

    def save(self, filename: Path):
        xc.io_utils.save_json_dict(filename, self.to_json())

    def update(self, value: str):
        if value == " " or value == "":
            self.status = CellStatus.EMPTY
            self.value = ""
        elif value is None:
            self.status = CellStatus.BLACK
            self.value = None
        elif isinstance(value, str) and len(value) == 1:
            self.status = CellStatus.SET
            self.value = value.upper()
        else:
            raise ValueError(f"Invalid input: {value}")

    def reset_cell(self):
        # Nothing to reset if locked
        if self.status == CellStatus.LOCKED or self.status == CellStatus.BLACK:
            return

        self.excluded.append(self.value)
        self.status = CellStatus.EMPTY
        self.value = ""
        self.queue = copy.deepcopy(self.queue_order)

        # Return the word (if any) that is now valid again
        removed_words = self.removed_words
        self.removed_words = []
        return removed_words

    def remove_word(self, word: str, direction: WordDirection):
        self.removed_words.append((word, direction))


class CellList(object):

    def __init__(self, cells: List[Cell]):
        self.cells = cells

        if self.cells[1].y > self.cells[0].y:
            self.direction = WordDirection.HORIZONTAL
        else:
            self.direction = WordDirection.VERTICAL

    def __getitem__(self, item):
        return self.cells[item]

    def __setitem__(self, key, value):
        self.cells[key] = value

    def __len__(self):
        return len(self.cells)

    def __str__(self):
        return ''.join([c.value or "-" for c in self.cells])

    def __repr__(self):
        origin = self.cells[0]
        return f"CellList \"{self}\": {{x={origin.x}, y={origin.y}, dir={self.direction}}}"

    def __iter__(self):
        return self.cells.__iter__()

    def has_empty_cell(self):
        return "-" in str(self)


class Grid(object):

    def __init__(self, grid_size: Tuple[int, int], corpus: xc.corpus.Corpus = None, shuffle: bool = True,
                 symmetry: GridSymmetry = GridSymmetry.ROTATIONAL, auto_symmetry: bool = False,
                 save_path: Union[None, Path] = None):

        # if grid_size[0] % 2 != 0 or grid_size[1] % 2 != 0:
        #     raise ValueError("Currently only even numbers are supported for grids")

        self.grid_size = grid_size
        self.row_count = self.grid_size[0]
        self.col_count = self.grid_size[1]

        assert (self.row_count >= 3)
        assert (self.col_count >= 3)

        self.h_heads = []
        self.v_heads = []

        self.corpus = corpus

        # Fill out grid/center
        self.grid = np.empty(self.grid_size, dtype=Cell)
        self.center = [((self.grid_size[0] - 1) / 2), ((self.grid_size[1] - 1) / 2)]

        # Fill out grid
        for i in range(self.row_count):
            for j in range(self.col_count):
                self.grid[i, j] = Cell(x=i, y=j, shuffle=shuffle)

        # Update the heads for horizontal and vertical clues
        self.update_length_and_head_data()

        self.auto_symmetry = auto_symmetry
        self.symmetry = symmetry
        self.save_path = save_path
        self.tries = []

    def __repr__(self):
        return f"Grid(dim=({self.grid_size[0]}, {self.grid_size[1]})"

    def __getitem__(self, x: Tuple[int, int]) -> Cell:
        # Check index
        if (x[0] < 0 or x[0] > self.grid_size[0]) or (x[1] < 0 or x[1] > self.grid_size[1]):
            raise IndexError(f"Index outside grid bounds:({self.grid_size[0]}, {self.grid_size[1]})")

        return self.grid[*x]

    def __setitem__(self, x: Tuple[int, int], value: str):
        self.set_grid(x[0], x[1], value)

    @classmethod
    def from_dict(cls, json_grid: dict):
        grid = cls(json_grid['grid_size'])
        grid.symmetry = GridSymmetry(json_grid['symmetry'])
        grid.auto_symmetry = json_grid['auto_symmetry']
        if 'grid_letters' in json_grid:
            grid_letters = json_grid['grid_letters']
            for i in range(grid.row_count):
                for j in range(grid.col_count):
                    grid.grid[i, j] = Cell.from_dict(grid_letters[i][j])

        grid.update_length_and_head_data()
        return grid

    @classmethod
    def load(cls, filepath: Path, **kwargs):
        new_grid = cls.from_dict(xc.io_utils.load_json(filepath), **kwargs)
        new_grid.save_path = filepath
        return new_grid

    @property
    def is_valid(self):
        return all([c.is_valid for c in self.grid.flatten()])

    # Saving ###############################################################

    def to_json(self):
        grid_letters = []
        for i in range(self.row_count):
            row = [self.grid[i, j].to_json() for j in range(self.col_count)]
            grid_letters.append(row)

        return dict(
            grid_size=self.grid_size,
            grid_letters=grid_letters,
            symmetry=self.symmetry.value,
            auto_symmetry=self.auto_symmetry
        )

    def count_possible(self,
                       query_cells: Union[CellList, List[Tuple[Cell, WordDirection]]],
                       grid_status: GridStatus = GridStatus.INCOMPLETE,
                       query_level: int = 2,
                       corpus=None) -> int:
        """ Count the number of configurations by varying a set of cell

        Args:
            query_cells:
            grid_status:
            query_level:
            corpus:

        Returns:

        """

        # Setup loop --------------------------------------------------------------------------------------------------#

        # End case for recursion
        if query_level == 0:
            return 0

        # To override corpus
        if not corpus:
            corpus = self.corpus

        # Count the number of entries given the candidate word
        n_possible = 0

        # Check through each of the query cells -----------------------------------------------------------------------#
        for qc in query_cells:

            # Get the cell/direction
            if hasattr(query_cells, 'direction'):
                cell = qc
                original_direction = query_cells.direction
            else:
                cell, original_direction = qc

            # Get the cells starting at {cell} in flip({direction})
            query_direction = WordDirection.flip(original_direction)
            query_cell_list = self.full_word_from_cell(cell.x,
                                                       cell.y,
                                                       query_direction,
                                                       terminate_on_empty=False)

            # Get the list of cells for the next level
            next_level_cells = []
            for c in query_cell_list:
                possible_next_cells = self.full_word_from_cell(c.x,
                                                               c.y,
                                                               query_direction,
                                                               terminate_on_empty=False)
                next_level_cells.extend(
                    [(next_cell, query_direction) for next_cell in possible_next_cells
                     if next_cell.is_start(query_direction)]
                )
            next_level_cells = list(set(next_level_cells))

            # No information available here
            if not query_cell_list.has_empty_cell():
                continue

            # Get the possible words
            c_candidate_words = xc.query.match(corpus, str(query_cell_list))

            # Recursively check other directions ---------------------------------------#
            head_cell = query_cell_list[0]
            for candidate_word in c_candidate_words:
                # Set the word (temporary)
                self.set_word(candidate_word.word, head_cell.x, head_cell.y, query_direction)

                # Recursive call to increment the number of possible words in next direction
                n_possible += self.count_possible(next_level_cells,
                                                  grid_status,
                                                  query_level - 1)

                # Reset values
                self.set_word(str(query_cell_list), head_cell.x, head_cell.y, query_direction)

            # Add to the possibilities if we're at the bottom query level
            n_possible += len(c_candidate_words)

            # Short circuit if we have reached an impossible grid configuration
            if len(c_candidate_words) == 0:
                return 0

        return n_possible

    def save(self, file_path: Union[None, Path] = None):
        if file_path:
            save_path = file_path
        elif self.save_path:
            save_path = self.save_path
        else:
            raise RuntimeError("Save path undefined")

        xc.io_utils.save_json_dict(save_path, self.to_json())

    def get_symmetric_index(self, x: int, y: int, symmetry: GridSymmetry):
        if symmetry == GridSymmetry.ROTATIONAL:
            coord_center = self.corner2center(x, y)
            coord_rot_center = -coord_center[0], -coord_center[1]
            return self.center2corner(*coord_rot_center)

    def build_tries(self, n: int = None):
        if self.corpus:
            if n:
                trie_len = n
            else:
                trie_len = max(self.row_count, self.col_count) + 1
            self.tries = self.corpus.to_n_tries(trie_len, padded=True)
        else:
            logger.warning("Could not build tries (no corpus loaded)")

    # Manipulation ###############################################################

    def set_grid(self,
                 x: int,
                 y: int,
                 value: Union[str, None]):
        # Check index
        if (x < 0 or x > self.grid_size[0]) or (y < 0 or y > self.grid_size[1]):
            raise IndexError(f"Index outside grid bounds:({self.grid_size[0]}, {self.grid_size[1]})")

        # Set value
        self.grid[x][y].update(value)

        # Set symmetry
        if self.symmetry != GridSymmetry.NONE:
            cr1, cr2 = self.get_symmetric_index(x, y, self.symmetry)

            if self.auto_symmetry and self.symmetry == GridSymmetry.ROTATIONAL:
                if self.grid[x][y].status != CellStatus.BLACK and \
                        self.grid[cr1][cr2].status == CellStatus.BLACK:
                    # If the rotated state is black, then reset that black square to default
                    self.grid[cr1][cr2].update("")

                elif self.grid[x][y].status == CellStatus.BLACK:
                    # Set the rotated state to black
                    self.grid[cr1][cr2].update(None)

        # Update heads
        self.update_length_and_head_data()

    def update_length_and_head_data(self):
        """ Compute/save word lengths, and which squares are origins
        """

        # Update horizontal / vertical heads
        self.h_heads = []
        self.v_heads = []
        answer_counter = 1
        for i in range(self.row_count):
            for j in range(self.col_count):

                # Update lists of head nodes
                is_h_start = self.is_h_start(i, j)
                is_v_start = self.is_v_start(i, j)

                if is_h_start:
                    self.h_heads.append((i, j))

                if is_v_start:
                    self.v_heads.append((i, j))

                if is_h_start or is_v_start:
                    self[i, j].answer_number = answer_counter
                    answer_counter += 1
                else:
                    self[i, j].answer_number = None

                # Update start/end data
                self[i, j].is_h_start = self.is_h_start(i, j)
                self[i, j].is_h_end = self.is_h_end(i, j)
                self[i, j].is_v_start = self.is_v_start(i, j)
                self[i, j].is_v_end = self.is_v_end(i, j)

        # Update word lengths
        for i in range(self.row_count):
            for j in range(self.col_count):
                self[i, j].hlen = self.horizontal_word_len(i, j)
                self[i, j].vlen = self.vertical_word_len(i, j)

    def clear(self):
        """ Reset all values in the grid, except those that are locked or black
        """
        for c in self.grid.flatten():
            if c.status == CellStatus.SET:
                c.reset_cell()

    def lock_entry(self, i: int, j: int):
        """ Lock the cell at [i, j]
        """

        # Change from set -> locked
        if self[i, j].status == CellStatus.SET:
            logger.debug(f"Entry [{i},{j}] status changed to LOCKED")
            self[i, j].status = CellStatus.LOCKED
        else:
            logger.error(f"Cannot lock entry [{i},{j}]: it is not currently set")

    def unlock_entry(self, i: int, j: int):
        """ Unlock the cell at [i, j]
        """

        # Change from locked -> set
        if self[i, j].status == CellStatus.LOCKED:
            logger.debug(f"Entry [{i},{j}] status changed to SET")
            self[i, j].status = CellStatus.SET
        else:
            logger.error(f"Cannot unlock entry [{i},{j}]: it is not currently locked")

    def toggle_locked(self, i: int, j: int):
        """ Flip the locked status of the cell at [i, j]
        """
        # Change from locked -> set
        if self[i, j].status == CellStatus.LOCKED:
            self[i, j].status = CellStatus.SET
            logger.debug(f"Entry [{i},{j}] status changed to SET")
        elif self[i, j].status == CellStatus.SET:
            logger.debug(f"Entry [{i},{j}] status changed to LOCKED")
            self[i, j].status = CellStatus.LOCKED
        else:
            logger.error(f"Cannot toggle locked status for entry [{i},{j}]: it is neither SET nor LOCKED")

    def set_word(self, word: str, i: int, j: int, direction: WordDirection, lock: bool = False):
        """
        Set word (or word fragment) in the grid beginning at index [i,j]

        Args:
            word: (str) word to set
            i (int): row of the beginning of the word
            j (int): column of the beginning of the word
            direction (WordDirection): direction of the word (vertical/horizontal)
            lock (bool): true if the status of cells containing the inputted word should be set to locked
        """

        match direction:
            case direction.HORIZONTAL:
                if self.col_count - j < len(word):
                    raise ValueError("Dimension Mismatch: Cannot fit word within horizontal section")

                for lix in range(len(word)):
                    self[i, j + lix].update(word[lix])
                    if lock:
                        self[i, j + lix].status = CellStatus.LOCKED
            case direction.VERTICAL:
                if self.row_count - i < len(word):
                    raise ValueError("Dimension Mismatch: Cannot fit word within vertical section")
                for lix in range(len(word)):
                    self[i + lix, j].update(word[lix])
                    if lock:
                        self[i + lix, j].status = CellStatus.LOCKED
            case _:
                raise ValueError("Invalid word direction")

    # Attributes ##################################################################

    def is_h_start(self, i: int, j: int) -> bool:
        if j > 0:
            is_after_black = (self[i, j - 1].status == xc.grid.CellStatus.BLACK and
                              self[i, j].status != xc.grid.CellStatus.BLACK)
        else:
            is_after_black = False

        return self[i, j].status != CellStatus.BLACK and (j == 0 or is_after_black)

    def is_h_end(self, i: int, j: int) -> bool:
        if j < self.col_count - 1:
            is_before_black = (self[i, j + 1].status == xc.grid.CellStatus.BLACK and
                               self[i, j].status != xc.grid.CellStatus.BLACK)
        else:
            is_before_black = False
        return self[i, j].status != CellStatus.BLACK and (j == (self.col_count - 1) or is_before_black)

    def is_v_start(self, i: int, j: int) -> bool:
        if i > 0:
            is_after_black = (self[i - 1, j].status == xc.grid.CellStatus.BLACK and
                              self[i, j].status != xc.grid.CellStatus.BLACK)
        else:
            is_after_black = False
        return self[i, j].status != CellStatus.BLACK and (i == 0 or is_after_black)

    def is_v_end(self, i: int, j: int) -> bool:
        if i < self.row_count - 1:
            is_before_black = (self[i + 1, j].status == xc.grid.CellStatus.BLACK and
                               self[i, j].status != xc.grid.CellStatus.BLACK)
        else:
            is_before_black = False
        return self[i, j].status != CellStatus.BLACK and (i == (self.row_count - 1) or is_before_black)

    def get_next_cell(self,
                      x: int,
                      y: int,
                      move_dir: MoveDirection) -> Cell:
        # Next square index
        i = x
        j = y

        # Save for readability
        on_left_column = j == 0
        on_right_column = j == (self.col_count - 1)
        on_top_row = i == 0
        on_bottom_row = i == (self.row_count - 1)

        match move_dir:
            case MoveDirection.FORWARD_HORIZONTAL:
                if on_bottom_row and on_right_column:
                    # Can't proceed forward
                    return self[i, j]
                if j < self.col_count - 1:
                    j += 1
                elif j == self.col_count - 1 and i < self.row_count - 1:
                    j = 0
                    i += 1

            case MoveDirection.FORWARD_VERTICAL:
                if not on_bottom_row:
                    i += 1
                elif not on_right_column:
                    i = 0
                    j += 1
                else:
                    # Can't proceed forward
                    return self[i, j]

            case MoveDirection.BACK_HORIZONTAL:

                if not on_left_column:
                    j -= 1
                elif not on_top_row:
                    i -= 1
                    j = self.col_count - 1
                else:
                    # Can't proceed forward
                    return self[i, j]

            case MoveDirection.BACK_VERTICAL:

                if not on_top_row:
                    # Move one square up the left
                    i -= 1
                elif not on_left_column:
                    # Cannot move up further
                    return self[self.row_count - 1, j - 1]
                else:
                    return self[i, j]

        if self[i, j].status == CellStatus.BLACK:
            return self.get_next_cell(i, j, move_dir)
        else:
            return self[i, j]

    # Utilities ###############################################################

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

    def full_word_from_cell(self,
                            x: int,
                            y: int,
                            direction: WordDirection,
                            terminate_on_empty=False) -> CellList:

        start_cell = self[x, y]

        if start_cell.status == CellStatus.BLACK:
            return CellList([])

        match direction:
            case direction.VERTICAL:
                pre_traverse_dir = GridDirection.UP
                pos_traverse_dir = GridDirection.DOWN
            case direction.HORIZONTAL:
                pre_traverse_dir = GridDirection.LEFT
                pos_traverse_dir = GridDirection.RIGHT
            case _:
                raise ValueError("Invalid direction")

        start_cells = list(reversed(
            self.aggregate_cells(x, y, pre_traverse_dir, terminate_on_empty)[1:]
        ))
        end_cells = self.aggregate_cells(x, y, pos_traverse_dir, terminate_on_empty)[1:]
        cells = start_cells + [start_cell] + end_cells
        return CellList(cells)

    def aggregate_cells(self, i: int, j: int,
                        which: GridDirection,
                        terminate_on_empty=False) -> List[Cell]:
        cells = [self[i, j]]

        # Nothing to aggregate if we're starting at a black square
        if cells[0].status == CellStatus.BLACK:
            return []

        match which:
            case GridDirection.UP:
                def termination_criteria(c):
                    return c.is_v_start or (terminate_on_empty and c.status == CellStatus.EMPTY)

                def update(c):
                    return self[c.x - 1, c.y]
            case GridDirection.DOWN:
                def termination_criteria(c):
                    return c.is_v_end or (terminate_on_empty and c.status == CellStatus.EMPTY)

                def update(c):
                    return self[c.x + 1, c.y]
            case GridDirection.LEFT:
                def termination_criteria(c):
                    return c.is_h_start or (terminate_on_empty and c.status == CellStatus.EMPTY)

                def update(c):
                    return self[c.x, c.y - 1]
            case GridDirection.RIGHT:
                def termination_criteria(c):
                    return c.is_h_end or (terminate_on_empty and c.status == CellStatus.EMPTY)

                def update(c):
                    return self[c.x, c.y + 1]
            case _:
                raise ValueError("invalid direction encountered")

        while not termination_criteria(cells[-1]):
            cells.append(update(cells[-1]))

        return cells

    def word_len(self, i: int, j: int, direction: WordDirection):
        return len(self.full_word_from_cell(i, j, direction))

    def horizontal_word_len(self, i: int, j: int):
        return self.word_len(i, j, WordDirection.HORIZONTAL)

    def vertical_word_len(self, i: int, j: int):
        return self.word_len(i, j, WordDirection.VERTICAL)

    # Output ###############################################################

    def to_str(self, delimiter="\n"):
        out_str = ""
        for i in range(self.grid_size[0]):
            grid_vals = []
            for x in self.grid[i]:
                match x.status:
                    case CellStatus.EMPTY:
                        gv = "-"
                    case CellStatus.BLACK:
                        gv = "■"
                    case _:
                        gv = x.value

                grid_vals += gv

            out_str += " ".join(grid_vals)

            if i < self.grid_size[0] - 1:
                out_str += delimiter
        return out_str

    def print(self):
        self.to_console()

    def to_console(self):
        print(self.to_str())

    def print_boundaries(self):
        out_str = ""
        for i in range(self.row_count):
            grid_vals = []
            for j in range(self.col_count):
                if self.is_h_start(i, j) and self.is_v_start(i, j):
                    gv = "x"
                elif self.is_h_end(i, j) and self.is_v_end(i, j):
                    gv = "X"
                elif self.is_h_start(i, j) and self.is_v_end(i, j):
                    gv = "y"
                elif self.is_h_end(i, j) and self.is_v_start(i, j):
                    gv = "Y"
                elif self.is_h_start(i, j):
                    gv = "h"
                elif self.is_v_start(i, j):
                    gv = "v"
                elif self.is_h_end(i, j):
                    gv = "H"
                elif self.is_v_end(i, j):
                    gv = "V"
                else:
                    gv = "-"

                grid_vals += gv

            out_str += " ".join(grid_vals)

            if i < self.grid_size[0] - 1:
                out_str += "\n"
        print(out_str)

    def print_lens(self, direction: WordDirection):
        out_str = ""
        for i in range(self.grid_size[0]):
            grid_vals = []
            for j in range(self.col_count):
                match direction:
                    case WordDirection.HORIZONTAL:
                        grid_vals += str(self[i, j].hlen)
                    case WordDirection.VERTICAL:
                        grid_vals += str(self[i, j].vlen)

            out_str += " ".join(grid_vals)

            if i < self.grid_size[0] - 1:
                out_str += "\n"
        print(out_str)


if __name__ == '__main__':
    lc = xc.corpus.Corpus.from_test()
    g = Grid((5, 5), lc)
    g.set_grid(1, 1, 'B')
    g.set_grid(2, 2, 'F')
    g[2, 2].status = CellStatus.LOCKED
    g[4, 4].status = CellStatus.BLACK

    x1, x2 = 0, 2
    c1, c2 = g.corner2center(x1, x2)

    g.to_console()

    test_file = Path(xc.crosscosmos_project_root / "test_grid.xc")
    # g.save(test_file)
    g2 = Grid.load(test_file)
    print()
    g2.to_console()
