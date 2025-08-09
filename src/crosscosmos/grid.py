"""
Defines a crossword Grid class, interfacing between the data and gui laters

"""

import copy
import logging
import random
import string
from pathlib import Path
from typing import Iterable

import numpy as np
import polars as pl
from numpy.typing import NDArray
from pydantic import BaseModel

from crosscosmos import constants, io_utils, query
from crosscosmos.corpus import Corpus
from crosscosmos.enums import (
    CellStatus,
    GridDirection,
    GridStatus,
    GridSymmetry,
    MoveDirection,
    WordDirection,
)
from crosscosmos.wordlists.lafarge import LaFargeWord

logger = logging.getLogger(__name__)


class Cell:
    """Individual cell in a crossword grid.

    Manages the state, value, and constraints of a single grid position.
    Tracks word boundaries, removed words, and maintains a queue of
    possible letters for solving.

    Parameters
    ----------
    x : int
        Row coordinate in the grid
    y : int
        Column coordinate in the grid
    status : CellStatus, optional
        Initial cell status (default: EMPTY)
    value : str, optional
        Letter value of the cell (default: "")
    gui_coordinates : tuple[float, float] | None, optional
        GUI display coordinates
    shuffle : bool, optional
        Whether to shuffle the letter queue (default: True)

    TODO:
         -Remove solve attributes
         - Make a frozen dataclass

    Attributes
    ----------
    queue : list[str]
        Available letters to try in this cell
    removed_words : list[tuple[str, WordDirection]]
        Words that were removed from tries when this cell was filled
    hlen : int
        Length of horizontal word containing this cell
    vlen : int
        Length of vertical word containing this cell
    """

    def __init__(
        self,
        x: int,
        y: int,
        status: CellStatus = CellStatus.EMPTY,
        value: str = "",
        gui_coordinates: tuple[float, float] | None = None,
        shuffle: bool = True,
    ):
        self.x: int = x
        self.y: int = y
        self.matrix_index: tuple[int, int] = (x, y)
        self.status: CellStatus = status
        self.value: str = value
        self.gui_coordinates: tuple[int, int] | None = gui_coordinates
        self.gui_row: int | None = None
        self.gui_col: int | None = None

        # Word boundary flags
        self.is_h_start: bool = False
        self.is_h_end: bool = False
        self.is_v_start: bool = False
        self.is_v_end: bool = False
        self.answer_number: int | None = None

        # Solving state (TODO-remove)
        self.removed_words: list[tuple[str, WordDirection]] = []
        self.excluded: list[str] = []

        # Letter queue for solving
        self.queue_order: list[str] = list(reversed(string.ascii_uppercase))
        self.queue: list[str] = copy.deepcopy(self.queue_order)
        self.shuffle_for_solving = shuffle
        if self.shuffle_for_solving:
            self.shuffle()

    def __repr__(self):
        return f"Cell(val='{self.value}',loc={self.matrix_index},status={self.status})"

    def shuffle(self) -> None:
        """Shuffles the letter queue."""
        random.shuffle(self.queue)

    def is_start(self, direction: WordDirection | int) -> bool:
        """Check if cell starts a word in given direction (HORIZONTAL=0 or VERTICAL=1)."""
        match WordDirection(direction):
            case WordDirection.HORIZONTAL:
                return self.is_h_start
            case WordDirection.VERTICAL:
                return self.is_v_start
            case _:
                raise ValueError("Invalid WordDirection")

    def is_end(self, direction: WordDirection | int) -> bool:
        """Check if cell ends a word in given direction (HORIZONTAL=0 or VERTICAL=1)."""
        match WordDirection(direction):
            case WordDirection.HORIZONTAL:
                return self.is_h_end
            case WordDirection.VERTICAL:
                return self.is_v_end
            case _:
                raise ValueError("Invalid WordDirection")

    def update(self, value: str | None) -> None:
        """Update cell value and status.

        Parameters
        ----------
        value : str | None
            New value: single letter, placeholder ('?','-', or ' '), empty string, or None for black

        Raises
        ------
        ValueError
            If value is invalid (not single character or special value)
        """
        if value == "" or value in constants.PLACEHOLDERS:
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


    def reset_cell(self) -> list[tuple[str, WordDirection]]:
        """Reset cell to empty state.

        Clears the cell value and restores the letter queue.
        Returns any words that were removed when this cell was filled.

        Returns
        -------
        list[tuple[str, WordDirection]]
            Words that should be restored to tries
        """
        if self.status in (CellStatus.LOCKED, CellStatus.BLACK):
            return []

        self.excluded.append(self.value)
        self.status = CellStatus.EMPTY
        self.value = ""
        self.queue = copy.deepcopy(self.queue_order)

        removed_words = self.removed_words
        self.removed_words = []
        return removed_words

    def remove_word(self, word: str, direction: WordDirection | int) -> None:
        """Track a word removed from the trie due to this cell.

        Parameters
        ----------
        word : str
            Word that was removed
        direction : WordDirection
            Direction of the removed word
        """
        self.removed_words.append((word, WordDirection(direction)))

    def to_json(self) -> dict:
        """Serialize cell to JSON-compatible dictionary.

        Returns
        -------
        dict
            Cell data as dictionary
        """
        return {
            "status": self.status.value,
            "value": self.value,
            "matrix_index": self.matrix_index,
            "x": self.x,
            "y": self.y,
            "gui_coordinates": self.gui_coordinates,
            "gui_row": self.gui_row,
            "gui_col": self.gui_col,
            "is_h_start": self.is_h_start,
            "is_h_end": self.is_h_end,
            "is_v_start": self.is_v_start,
            "is_v_end": self.is_v_end,
            "answer_number": self.answer_number,
        }

    @classmethod
    def from_dict(cls, json_cell: dict, **kwargs) -> "Cell":
        """Create cell from dictionary representation.

        Parameters
        ----------
        json_cell : dict
            Dictionary containing cell data

        Returns
        -------
        Cell
            Reconstructed cell object
        """
        cell = cls(
            x=json_cell["x"],
            y=json_cell["y"],
            status=CellStatus(json_cell["status"]),
            value=json_cell["value"],
            gui_coordinates=json_cell["gui_coordinates"],
            **kwargs,
        )
        cell.matrix_index = tuple(json_cell["matrix_index"])
        cell.gui_row = json_cell["gui_row"]
        cell.gui_col = json_cell["gui_col"]
        cell.is_h_start = json_cell["is_h_start"]
        cell.is_h_end = json_cell["is_h_end"]
        cell.is_v_start = json_cell["is_v_start"]
        cell.is_v_end = json_cell["is_v_end"]
        cell.answer_number = json_cell["answer_number"]
        return cell

    @classmethod
    def load(cls, filename: Path, **kwargs) -> "Cell":
        """Load cell from JSON file, with additional arguments passed to constructor"""
        return cls.from_dict(io_utils.load_json(filename), **kwargs)

    def save(self, filename: Path) -> None:
        """Save cell to JSON file."""
        io_utils.save_json_dict(filename, self.to_json())


class Entry:
    """Ordered collection of cells forming a word or partial word.

    Provides convenient access to cells that form a continuous
    sequence in the grid, typically representing a word slot.

    Attributes
    ----------
    cells: list[Cell]
        List of cells that make up this entry
    partial_entry:
        If true, this is only a partial entry and not the complete word
    direction : WordDirection
        Direction of the cell sequence (auto-detected)
    """

    def __init__(self, cells: list[Cell], partial_entry: bool = False):
        self.cells: list[Cell] = cells
        self.partial_entry = partial_entry

        # Auto-detect direction based on cell positions
        if not self.cells or len(self.cells) < 2:
            self.direction = WordDirection.HORIZONTAL
        elif self.cells[1].y > self.cells[0].y:
            self.direction = WordDirection.HORIZONTAL
        else:
            self.direction = WordDirection.VERTICAL

    @property
    def direction_char(self) -> str:
        """Direction charaction: "A" (accross) or "D" (down) """
        return self.direction.char()

    @property
    def entry_id(self) -> str:
        """Entry identifier (e.g., "1A" or "10D") """
        return f"{self.cells[0].answer_number}{self.direction_char}"

    @property
    def is_complete(self) -> bool:
        """If true, the entry is complete (no empty cells)"""
        return not any(c.status == CellStatus.EMPTY for c in self.cells)

    def __getitem__(self, item) -> Cell:
        """ Returns the cell at a given index. """
        return self.cells[item]

    def __setitem__(self, key, value):
        """ Sets the value of the cell at a given index. """
        self.cells[key] = value

    def __len__(self) -> int:
        """Length of the entry (number of cells / characters in the entry). """
        return len(self.cells)

    def __iter__(self) -> Iterable[Cell]:
        return iter(self.cells)

    def __str__(self) -> str:
        """String representation showing letters/placeholders."""
        return "".join([c.value or "-" for c in self.cells])

    def __repr__(self) -> str:
        origin = self.cells[0]
        return f'Entry {self.entry_id}: "{self}" (x={origin.x},y={origin.y},length={len(self)})'


    @property
    def x_range(self) -> tuple[int, int]:
        """Gets the range of x values of this word in the grid"""
        x_vals = [c.x for c in self.cells]
        return min(x_vals), max(x_vals)

    @property
    def y_range(self) -> tuple[int, int]:
        """Gets the range of x values of this word in the grid"""
        y_vals = [c.y for c in self.cells]
        return min(y_vals), max(y_vals)

    def has_empty_cell(self) -> bool:
        """Check if any cells are empty"""
        return any(x for x in str(self) if x in constants.PLACEHOLDERS)

    def truncate_end(self) -> str:
        """ Returns a string of this entry with any placeholder characters from the end removed
        TODO- why is this here?
        """
        return str(self).rstrip("".join(constants.PLACEHOLDERS))

    def to_first_placeholder(self) -> str:
        cell_str = str(self)
        for i, char in enumerate(cell_str):
            if char in constants.PLACEHOLDERS:
                return cell_str[:i]
        return cell_str


class Grid:
    """Crossword grid with solving and manipulation capabilities.

    Manages a 2D array of cells, tracks word slots, handles symmetry,
    and provides methods for setting words and solving puzzles.

    Parameters
    ----------
    grid_size : tuple[int, int]
        Dimensions as (rows, columns)
    corpus : Corpus, optional
        Word corpus for solving
    shuffle : bool, optional
        Whether to shuffle letter queues (default: True)
    symmetry : GridSymmetry, optional
        Grid symmetry type (default: ROTATIONAL)
    auto_symmetry : bool, optional
        Whether to automatically apply symmetry (default: False)
    save_path : Path | None, optional
        Default save location

    Attributes
    ----------
    grid : np.ndarray[Cell]
        2D array of cells
    tries : list[pygtrie.Trie]
        Tries indexed by word length for solving
    h_heads : list[tuple[int, int]]
        Starting positions of horizontal words
    v_heads : list[tuple[int, int]]
        Starting positions of vertical words
    """

    def __init__(
        self,
        grid_size: tuple[int, int],
        corpus: Corpus | None = None,
        shuffle: bool = True,
        symmetry: GridSymmetry = GridSymmetry.ROTATIONAL,
        auto_symmetry: bool = False,
        save_path: Path | str | None = None,
    ):
        # Validate dimensions
        self.grid_size = grid_size
        self.row_count = grid_size[0]
        self.col_count = grid_size[1]

        if self.row_count < 3 or self.col_count < 3:
            raise ValueError("Grid dimensions must be at least 3x3")

        # Initialize grid
        self.grid: NDArray[Cell] = np.empty(self.grid_size, dtype=Cell)
        self.center = [(self.row_count - 1) / 2, (self.col_count - 1) / 2]

        for i in range(self.row_count):
            for j in range(self.col_count):
                self.grid[i, j] = Cell(x=i, y=j, shuffle=shuffle)

        # Word tracking
        self.h_heads = []
        self.v_heads = []

        # Corpus and solving
        if corpus:
            max_len = max(self.row_count, self.col_count)
            self.corpus = corpus.max_length(max_len)
        else:
            self.corpus = None
        self.tries = []

        # Grid properties
        self.symmetry: GridSymmetry = symmetry
        self.auto_symmetry: bool = auto_symmetry
        self.save_path = save_path if not save_path else Path(save_path)

        # Initialize word boundaries
        self.update_length_and_head_data()

    def __str__(self) -> str:
        return self.to_str()

    def __repr__(self) -> str:
        return f"Grid(dim=({self.row_count}, {self.col_count}))"

    def __getitem__(self, key: tuple[int, int] | str) -> Cell | Entry | None:
        """Get cell at coordinates.

        Parameters
        ----------
        key : tuple[int, int] or str
            Coordinates as (row, column) or an entry id ("19D", etc)

        Returns
        -------
        Cell or Entry
            Cell at given position or Entry associated with the given entry ID

        Raises
        ------
        IndexError
            If coordinates are out of bounds
        """
        if isinstance(key, tuple):
            x, y = key
            if x < 0 or x >= self.row_count or y < 0 or y >= self.col_count:
                raise IndexError(f"Index {key} outside grid bounds: ({self.row_count}, {self.col_count})")
            return self.grid[x, y]
        elif isinstance(key, str):
            return self.get_entry(key)
        else:
            raise ValueError(f"Unexpeted key: {key}")

    def __setitem__(self, key: tuple[int, int], value: str | None) -> None:
        """Set cell value at coordinates.

        Parameters
        ----------
        key : tuple[int, int]
            Coordinates as (row, column)
        value : str | None
            New cell value
        """
        self.set_grid(key[0], key[1], value)

    @property
    def is_valid(self) -> bool:
        """Check if all cells form valid crossings."""
        return all(self.is_cell_valid(c.x, c.y) for c in self.grid.flatten())

    @property
    def entry_starts(self) -> pl.DataFrame:
        """Get dataframe of horizontal word starts."""
        return pl.concat([self.h_starts, self.v_starts])

    @property
    def h_starts(self) -> pl.DataFrame:
        """Get dataframe of horizontal word starts."""
        df = self.to_dataframe().filter(pl.col("is_h_start"))
        df = df.with_columns(
            pl.col("matrix_index")
            .map_elements(lambda row: self.get_entry_id(row[0], row[1], WordDirection.HORIZONTAL), return_dtype=pl.String)
            .alias("entry_id")
        )
        return df

    @property
    def v_starts(self) -> pl.DataFrame:
        """Get dataframe of vertical word starts."""
        df = self.to_dataframe().filter(pl.col("is_v_start"))
        df = df.with_columns(
            pl.col("matrix_index")
            .map_elements(lambda row: self.get_entry_id(row[0], row[1], WordDirection.VERTICAL), return_dtype=pl.String)
            .alias("entry_id")
        )
        return df

    @classmethod
    def from_dict(cls, json_grid: dict, **kwargs) -> "Grid":
        """Create grid from dictionary representation."""
        grid = cls(grid_size=json_grid["grid_size"], **kwargs)
        grid.symmetry = GridSymmetry(json_grid["symmetry"])
        grid.auto_symmetry = json_grid["auto_symmetry"]

        if "grid_letters" in json_grid:
            grid_letters = json_grid["grid_letters"]
            for i in range(grid.row_count):
                for j in range(grid.col_count):
                    grid.grid[i, j] = Cell.from_dict(grid_letters[i][j])

        grid.update_length_and_head_data()
        return grid

    @classmethod
    def load(cls, filepath: Path | str, **kwargs) -> "Grid":
        """Load grid from JSON file."""
        grid = cls.from_dict(io_utils.load_json(filepath), **kwargs)
        grid.save_path = filepath
        return grid

    def entries(self, with_db_counts: bool = True) -> pl.DataFrame:
        df_data = {
            "entry_id": [],
            "entry": [],
            "length": [],
            "score": [],
            "complete": [],
            "start_x": [],
            "start_y": [],
            "end_x": [],
            "end_y": [],
            "direction": [],
            "entry_num": [],
        }

        def process_entries(starts_df: pl.DataFrame, direction: WordDirection):
            """Process all entries in a given direction."""

            for c in starts_df.rows(named=True):
                entry = self.cell_to_entry(c["x"], c["y"], direction)
                if not entry:
                    raise RuntimeError(f"No entry found, despite being marked as a start. This should never happen!")
                entry_str = str(entry)

                # Calculate end coordinates based on direction
                if direction == WordDirection.HORIZONTAL:
                    end_x, end_y = c["x"], c["y"] + len(entry) - 1
                else:  # VERTICAL
                    end_x, end_y = c["x"] + len(entry) - 1, c["y"]

                # Add entry data
                df_data["start_x"].append(c["x"])
                df_data["start_y"].append(c["y"])
                df_data["direction"].append(direction.char())
                df_data["end_x"].append(end_x)
                df_data["end_y"].append(end_y)
                df_data["entry"].append(str(entry))
                df_data["length"].append(len(entry))
                df_data["entry_id"].append(entry.entry_id)
                df_data["entry_num"].append(c["answer_number"])

                # Check completion and get score
                complete = not any(ch in entry_str for ch in constants.PLACEHOLDERS)
                df_data["complete"].append(complete)

                score = None
                # if complete:
                #     word = query.Query(default=False).db.get(word=entry_str)
                #     if word:
                #         score = word.score
                df_data["score"].append(score)

        # Process both directions
        process_entries(self.h_starts, WordDirection.HORIZONTAL)
        process_entries(self.v_starts, WordDirection.VERTICAL)

        return pl.DataFrame(df_data)

    def is_cell_valid(self, i: int, j: int) -> bool:
        """Check if both crossings at a given cell are valid (>=3 letters)"""
        is_black = self.grid[i, j].status == CellStatus.BLACK
        hlen = self.word_len(i, j, WordDirection.HORIZONTAL)
        vlen = self.word_len(i, j, WordDirection.VERTICAL)
        return is_black or (hlen >= 3 and vlen >= 3)

    def clone(self):
        """Clone (deepcopy) this grid"""
        return copy.deepcopy(self)

    def shuffle(self):
        """Shuffles the queue in all cells"""
        for c in self.grid.flatten():
            c.shuffle()

    def build_tries(self, n: int | None = None) -> None:
        """Build tries from corpus for each word length.

        TODO
        ----
        Remove from this class

        Parameters
        ----------
        n : int | None, optional
            Maximum word length (default: max of grid dimensions)
        """
        if not self.corpus:
            logger.warning("Cannot build tries without corpus")
            return

        trie_len = n or max(self.row_count, self.col_count)
        self.tries = self.corpus.to_n_tries(trie_len, padded=True)

    def reset_for_solving(self) -> None:
        """Reset grid to prepare for a new solving attempt.

        Clears all non-locked/non-black cells, rebuilds letter queues,
        and reconstructs tries from the corpus.
        """
        # Reset cells
        for i in range(self.row_count):
            for j in range(self.col_count):
                cell = self[i, j]
                if cell.status in (CellStatus.BLACK, CellStatus.LOCKED):
                    continue

                cell.reset_cell()
                # Rebuild queue with shuffling if originally shuffled
                if cell.shuffle_for_solving:
                    cell.shuffle()
                    # cell.queue = copy.deepcopy(cell.queue_order)
                    # random.shuffle(cell.queue)

        # Rebuild tries and update grid metadata
        self.build_tries()
        self.update_length_and_head_data()

    def set_grid(self, x: int, y: int, value: str | None) -> None:
        """Set cell value with symmetry handling.

        Updates the cell at the given position and applies symmetry
        rules if enabled.

        Parameters
        ----------
        x : int
            Row coordinate
        y : int
            Column coordinate
        value : str | None
            New value (letter, empty string, or None for black)

        Raises
        ------
        IndexError
            If coordinates are out of bounds
        """
        # Validate coordinates
        if x < 0 or x >= self.row_count or y < 0 or y >= self.col_count:
            raise IndexError(f"Index ({x}, {y}) outside grid bounds")

        # Set primary cell
        self.grid[x][y].update(value)

        # Apply symmetry
        if self.auto_symmetry and self.symmetry == GridSymmetry.ROTATIONAL:
            sym_x, sym_y = self.get_symmetric_index(x, y, self.symmetry)

            if self.grid[x][y].status == CellStatus.BLACK:
                self.grid[sym_x][sym_y].update(None)
            elif self.grid[sym_x][sym_y].status == CellStatus.BLACK:
                self.grid[sym_x][sym_y].update("")

        # Update word boundaries
        self.update_length_and_head_data()

    def get_symmetric_index(self, x: int, y: int, symmetry: GridSymmetry) -> tuple[int, int]:
        """Calculate symmetric position for a cell.

        Parameters
        ----------
        x : int
            Row coordinate
        y : int
            Column coordinate
        symmetry : GridSymmetry
            Type of symmetry to apply

        Returns
        -------
        tuple[int, int]
            Symmetric coordinates
        """
        if symmetry == GridSymmetry.ROTATIONAL:
            center_x, center_y = self.corner2center(x, y)
            return self.center2corner(-center_x, -center_y)
        # TODO- Add other symmetry types as needed (reflectional)
        return x, y

    def update_length_and_head_data(self) -> None:
        """Update word boundaries, lengths, and numbering.

        Scans the grid to identify word starts/ends, calculate
        word lengths, and assign answer numbers.
        """
        self.h_heads = []
        self.v_heads = []
        answer_counter = 1

        # First pass: identify starts and assign numbers
        for i in range(self.row_count):
            for j in range(self.col_count):
                cell = self[i, j]

                # Check word boundaries
                cell.is_h_start = self._is_h_start(i, j)
                cell.is_h_end = self._is_h_end(i, j)
                cell.is_v_start = self._is_v_start(i, j)
                cell.is_v_end = self._is_v_end(i, j)

                # Track head positions
                if cell.is_h_start:
                    self.h_heads.append((i, j))
                if cell.is_v_start:
                    self.v_heads.append((i, j))

                # Assign answer numbers
                if cell.is_h_start or cell.is_v_start:
                    cell.answer_number = answer_counter
                    answer_counter += 1
                else:
                    cell.answer_number = None

    def clear(self) -> None:
        """Clear all non-locked, non-black cells."""
        for cell in self.grid.flatten():
            if cell.status == CellStatus.SET:
                cell.reset_cell()

    def lock_cell(self, i: int, j: int) -> None:
        """Lock a cell to prevent changes during solving.

        Parameters
        ----------
        i : int
            Row coordinate
        j : int
            Column coordinate
        """
        if self[i, j].status == CellStatus.SET:
            self[i, j].status = CellStatus.LOCKED
            logger.debug(f"Entry [{i},{j}] locked")
        else:
            logger.error(f"Cannot lock entry [{i},{j}]: not currently set")

    def unlock_cell(self, i: int, j: int) -> None:
        """Unlock a previously locked cell.

        Parameters
        ----------
        i : int
            Row coordinate
        j : int
            Column coordinate
        """
        if self[i, j].status == CellStatus.LOCKED:
            self[i, j].status = CellStatus.SET
            logger.debug(f"Entry [{i},{j}] unlocked")
        else:
            logger.error(f"Cannot unlock entry [{i},{j}]: not currently locked")

    def toggle_locked(self, i: int, j: int) -> None:
        """Toggle locked status of a cell.

        Parameters
        ----------
        i : int
            Row coordinate
        j : int
            Column coordinate
        """
        cell = self[i, j]
        if cell.status == CellStatus.LOCKED:
            cell.status = CellStatus.SET
            logger.debug(f"Entry [{i},{j}] unlocked")
        elif cell.status == CellStatus.SET:
            cell.status = CellStatus.LOCKED
            logger.debug(f"Entry [{i},{j}] locked")
        else:
            logger.error(f"Cannot toggle lock: [{i},{j}] is {cell.status}")

    def set_black(self, i: int, j: int, n: int = 1, direction: WordDirection | int = WordDirection.HORIZONTAL):
        black_sequence = [None] * n
        self.set_word(black_sequence, i, j, direction)

    def set_word(
        self, word: str | list[str | None], i: int, j: int, direction: WordDirection | int, lock: bool = False
    ) -> None:
        """Place a word in the grid.

        Parameters
        ----------
        word : str or list[str|None]
            Word to place (can include placeholders)
        i : int
            Starting row coordinate
        j : int
            Starting column coordinate
        direction : WordDirection
            Direction to place word
        lock : bool, optional
            Whether to lock the cells (default: False)

        Raises
        ------
        ValueError
            If word doesn't fit in grid
        """
        match WordDirection(direction):
            case WordDirection.HORIZONTAL:
                if self.col_count - j < len(word):
                    raise ValueError("Word too long for horizontal space")
                for idx, letter in enumerate(word):
                    self[i, j + idx].update(letter)
                    if lock:
                        self[i, j + idx].status = CellStatus.LOCKED

            case WordDirection.VERTICAL:
                if self.row_count - i < len(word):
                    raise ValueError("Word too long for vertical space")
                for idx, letter in enumerate(word):
                    self[i + idx, j].update(letter)
                    if lock:
                        self[i + idx, j].status = CellStatus.LOCKED

            case _:
                raise ValueError("Invalid word direction")

        self.update_length_and_head_data()

    def cell_to_entry(
        self, x: int, y: int, direction: WordDirection, terminate_on_empty: bool = False
    ) -> Entry | None:
        """Get all cells forming a word from a given position.

        Parameters
        ----------
        x : int
            Starting row coordinate
        y : int
            Starting column coordinate
        direction : WordDirection
            Direction of the word
        terminate_on_empty : bool, optional
            Stop at first empty cell (default: False)

        Returns
        -------
        Entry
            Cells forming the complete word
        """
        start_cell = self[x, y]
        if start_cell.status == CellStatus.BLACK:
            return None

        # Determine traversal directions
        if direction == WordDirection.VERTICAL:
            pre_dir = GridDirection.UP
            post_dir = GridDirection.DOWN
        else:
            pre_dir = GridDirection.LEFT
            post_dir = GridDirection.RIGHT

        # Collect cells before and after start position
        pre_cells = self._traverse_cells(x, y, pre_dir, terminate_on_empty)
        post_cells = self._traverse_cells(x, y, post_dir, terminate_on_empty)

        # Combine in correct order
        entry_cells = [*list(reversed(pre_cells[1:])), start_cell, *post_cells[1:]]

        # Create entry ID
        return Entry(entry_cells, partial_entry=False)

    def word_len(self, i: int, j: int, direction: WordDirection) -> int:
        """Get length of word at position (i, j)."""
        return len(self.cell_to_entry(i, j, direction))

    def get_next_cell(self, x: int, y: int, move_dir: MoveDirection) -> Cell:
        """Get next cell in solving order.

        Moves through grid left-to-right, top-to-bottom, skipping black cells.

        Parameters
        ----------
        x : int
            Current row
        y : int
            Current column
        move_dir : MoveDirection
            Direction to move

        Returns
        -------
        Cell
            Next cell (or current if can't move)
        """
        i, j = x, y

        match MoveDirection(move_dir):
            case MoveDirection.FORWARD_HORIZONTAL:
                if j < self.col_count - 1:
                    j += 1
                elif i < self.row_count - 1:
                    i += 1
                    j = 0
                else:
                    return self[i, j]  # Can't move forward

            case MoveDirection.FORWARD_VERTICAL:
                if i < self.row_count - 1:
                    i += 1
                elif j < self.col_count - 1:
                    j += 1
                    i = 0
                else:
                    return self[i, j]

            case MoveDirection.BACK_HORIZONTAL:
                if j > 0:
                    j -= 1
                elif i > 0:
                    i -= 1
                    j = self.col_count - 1
                else:
                    return self[i, j]

            case MoveDirection.BACK_VERTICAL:
                if i > 0:
                    i -= 1
                elif j > 0:
                    j -= 1
                    i = self.row_count - 1
                else:
                    return self[i, j]

        # Skip black cells
        if self[i, j].status == CellStatus.BLACK:
            return self.get_next_cell(i, j, move_dir)

        return self[i, j]

    def get_entry(self, entry_id: str) -> Entry | None:
        """Get cells forming a numbered word entry.

        Parameters
        ----------
        entry_id : str
            Entry identifier (e.g., "1A" or "10D")

        Returns
        -------
        Entry | None
            Cells forming the word, or None if not found

        Raises
        ------
        ValueError
            If entry_id format is invalid
        """

        if not entry_id or len(entry_id) < 2:
            raise ValueError(f"Invalid entry ID format: {entry_id}")

        try:
            entry_num = int(entry_id[:-1])
        except ValueError as e:
            raise ValueError(f"Invalid entry number in ID: {entry_id}") from e

        word_dir = WordDirection.from_char(entry_id[-1].upper())

        # Find matching entry in dataframe
        df = self.h_starts if word_dir == WordDirection.HORIZONTAL else self.v_starts
        entry = df.filter(pl.col("answer_number") == entry_num).to_dicts()
        if not entry:
            logger.error(f"Entry '{entry_id}' does not exist.")

        entry = entry[0]

        # Return the entry cells
        return self.cell_to_entry(entry["x"], entry["y"], direction=word_dir)

    def get_entry_id(self, x: int, y: int, direction: WordDirection) -> str | None:
        """ Gets the ID string (e.g., "6A") for a the entry at a given coordinate/diction combination
        """
        entry = self.cell_to_entry(x, y, direction=direction)
        if not entry:
            return None
        return entry.entry_id

    def get_crossers(self, entry_id: str) -> list[Entry]:
        """Find all words crossing a given entry.

        Parameters
        ----------
        entry_id : str
            Entry identifier (e.g., "1A" or "10D")

        Returns
        -------
        list[Entry]
            All crossing words
        """
        entry = self.get_entry(entry_id)
        if not entry:
            return []

        cross_dir = WordDirection.flip(entry.direction)
        return [self.cell_to_entry(cell.x, cell.y, cross_dir) for cell in entry]

    def count_possible(
        self,
        query_cells: Entry | list[tuple[Cell, WordDirection]],
        grid_status: GridStatus = GridStatus.INCOMPLETE,
        query_level: int = 2,
        corpus: Corpus | None = None,
    ) -> int:
        """Count possible word configurations for a cell set.

        Recursively explores possible word placements to estimate
        the difficulty of filling a region.

        Notes
        -----
        This has not been tested recently - needs to be updated to use Query!

        Parameters
        ----------
        query_cells : Entry | list[tuple[Cell, WordDirection]]
            Cells to analyze
        grid_status : GridStatus, optional
            Current grid status
        query_level : int, optional
            Recursion depth (default: 2)
        corpus : Corpus | None, optional
            Word corpus to use

        Returns
        -------
        int
            Number of possible configurations
        """
        if query_level == 0:
            return 0

        corpus = corpus or self.corpus
        if not corpus:
            return 0

        n_possible = 0

        for qc in query_cells:
            # Extract cell and direction
            if hasattr(query_cells, "direction"):
                cell = qc
                original_direction = query_cells.direction
            else:
                cell, original_direction = qc

            # Get perpendicular word
            query_direction = WordDirection.flip(original_direction)
            query_cell_list = self.cell_to_entry(cell.x, cell.y, query_direction, terminate_on_empty=False)

            if not query_cell_list.has_empty_cell():
                continue

            # Find matching words
            pattern = str(query_cell_list)
            candidate_words = query.match(corpus, pattern)

            if len(candidate_words) == 0:
                return 0  # Dead end

            # Prepare next level cells
            next_level_cells = []
            for c in query_cell_list:
                word_cells = self.cell_to_entry(c.x, c.y, original_direction, terminate_on_empty=False)
                next_level_cells.extend(
                    [(nc, original_direction) for nc in word_cells if nc.is_start(original_direction)]
                )
            next_level_cells = list(set(next_level_cells))

            # Try each candidate word
            head_cell = query_cell_list[0]
            for candidate in candidate_words:
                # Temporarily place word
                self.set_word(candidate.word, head_cell.x, head_cell.y, query_direction)

                # Recursive count
                n_possible += self.count_possible(next_level_cells, grid_status, query_level - 1, corpus)

                # Restore original state
                self.set_word(pattern, head_cell.x, head_cell.y, query_direction)

            n_possible += len(candidate_words)

        return n_possible

    def corner2center(self, x: int, y: int) -> tuple[float, float]:
        """Convert grid coordinates (x,y) to center-relative coordinates (c1,c2).

        Notes
        -----
        Given the following values:
            a: Corner -> Pt         [x,y]
            b: Corner -> Center     self.center
            c: Center -> Pt         [c1,c2]

        The Center-relative coordinates are computed as
            a = (b + c)    ->    C = (a - b)
            [c1,c2] = [x,y] - self.center

        Returns
        -------
        tuple[float, float]
            Coordinates relative to grid center (c1,c2).
        """
        return x - self.center[0], y - self.center[1]

    def center2corner(self, c1: float, c2: float) -> tuple[int, int]:
        """Convert center-relative coordinates (c1,c2) to grid coordinates (x,y).

        Notes
        -----
        Given the following values:
            A: Corner -> Pt         [x,y]
            B: Corner -> Center     self.center
            C: Center -> Pt         [c1,c2]

        The grid coordinates are computed as:
            A = (B + C)
            self.center + [c1,c2] = [x,y]

        Returns
        -------
        tuple[int, int]
            Grid coordinates (x,y)
        """
        return int(self.center[0] + c1), int(self.center[1] + c2)

    def word_lengths(self) -> pl.DataFrame:
        """Analyze word length distribution in grid.

        Returns
        -------
        pl.DataFrame
            Word lengths with counts and entry IDs
        """
        df = self.to_dataframe()

        # Process horizontal words
        h_starts = df.filter(pl.col("is_h_start"))
        h_starts = h_starts.with_columns([pl.lit("A").alias("dir"), pl.col("hlen").alias("word_len")])

        # Process vertical words
        v_starts = df.filter(pl.col("is_v_start"))
        v_starts = v_starts.with_columns([pl.lit("D").alias("dir"), pl.col("vlen").alias("word_len")])

        # Combine and aggregate
        cols = ["word_len", "answer_number", "dir"]
        all_starts = pl.concat([h_starts[cols], v_starts[cols]])

        return (
            all_starts.with_columns(
                pl.concat_str([pl.col("answer_number").cast(pl.Utf8), pl.col("dir")]).alias("entry_id")
            )
            .group_by("word_len")
            .agg([pl.len().alias("count"), pl.col("entry_id").alias("entries")])
            .sort("word_len")
        )

    def to_str(self, delimiter: str = "\n") -> str:
        """Convert grid to string representation.

        Parameters
        ----------
        delimiter : str, optional
            Line separator (default: newline)

        Returns
        -------
        str
            Grid as text with cells separated by spaces
        """
        lines = []
        for i in range(self.row_count):
            row_chars = []
            for j in range(self.col_count):
                cell = self[i, j]
                if cell.status == CellStatus.BLACK:
                    row_chars.append("■")
                elif cell.status == CellStatus.EMPTY:
                    row_chars.append("-")
                else:
                    row_chars.append(cell.value)
            lines.append(" ".join(row_chars))

        return delimiter.join(lines)

    def to_dataframe(self) -> pl.DataFrame:
        """Convert grid to dataframe representation."""
        return pl.DataFrame([c.to_json() for c in self.grid.flatten()])

    def print(self) -> None:
        """Print grid to console."""
        print(self.to_str())

    def to_console(self):
        """Print grid to console."""
        self.print()

    def print_boundaries(self, show_key: bool = True) -> None:
        """Print grid showing word start/end positions."""

        for i in range(self.row_count):
            row_chars = []
            for j in range(self.col_count):
                if self._is_h_start(i, j) and self._is_v_start(i, j):
                    char = "x"
                elif self._is_h_end(i, j) and self._is_v_end(i, j):
                    char = "X"
                elif self._is_h_start(i, j) and self._is_v_end(i, j):
                    char = "y"
                elif self._is_h_end(i, j) and self._is_v_start(i, j):
                    char = "Y"
                elif self._is_h_start(i, j):
                    char = "h"
                elif self._is_v_start(i, j):
                    char = "v"
                elif self._is_h_end(i, j):
                    char = "H"
                elif self._is_v_end(i, j):
                    char = "V"
                else:
                    char = "-"
                row_chars.append(char)
            print(" ".join(row_chars))

        if show_key:
            key_lines = [
                "x = horizontal start and vertical start",
                "X = horizontal end and vertical end",
                "y = horizontal start and vertical end",
                "Y = horizontal end and vertical start",
                "h = horizontal start only",
                "v = vertical start only",
                "H = horizontal end only",
                "V = vertical end only",
                "- = no start or end",
            ]
            print("Key:")
            for k in key_lines:
                print(f"    {k}")

    def print_lens(self, direction: WordDirection) -> None:
        """Print grid showing word lengths.

        Parameters
        ----------
        direction : WordDirection
            Which direction lengths to show
        """
        for i in range(self.row_count):
            row_vals = []
            for j in range(self.col_count):
                row_vals.append(str(self.word_len(i, j, direction)))
            print(" ".join(row_vals))

    def to_json(self) -> dict:
        """Serialize grid to JSON-compatible dictionary."""
        grid_letters = []
        for i in range(self.row_count):
            row = [self.grid[i, j].to_json() for j in range(self.col_count)]
            grid_letters.append(row)

        return {
            "grid_size": self.grid_size,
            "grid_letters": grid_letters,
            "symmetry": self.symmetry.value,
            "auto_symmetry": self.auto_symmetry,
        }

    def save(self, file_path: Path | None = None) -> None:
        """Save grid to JSON file.

        Parameters
        ----------
        file_path : Path | None, optional
            Save location (uses default if None)
        """
        save_path = file_path or self.save_path
        if save_path:
            io_utils.save_json_dict(save_path, self.to_json())

    def horizontal_word_len(self, i: int, j: int) -> int:
        """Get length of horizontal word containing cell at (i,j)"""
        return self.word_len(i, j, WordDirection.HORIZONTAL)

    def vertical_word_len(self, i: int, j: int) -> int:
        """Get length of vertical word containing cell at (i,j)"""
        return self.word_len(i, j, WordDirection.VERTICAL)

    def get_possible_words(
        self, entry_id: str, db=LaFargeWord, exclude: dict[int, list[str] | str] | None = None, **kwargs
    ) -> pl.DataFrame:
        """Get all possible words for a given entry given a data source and minimum score threshold

        Parameters
        ----------
        db : Pony database table
            Database of valid entries
        entry_id : str
            Cell ID, must be a number followed by "A" or "D" (e.g., '1A' or '10D')
        exclude : dict (index -> character list)
            Dictionary representing indices to exclude letters. For example {1: "A"} will filter all entires that have
            "A" as the first character
        kwargs
            passed to Query

        Returns
        -------
        pl.DataFrame
            DataFrame containing all valid words, ordred by their score
        """
        exclude = exclude or {}

        current_entry = self.get_entry(entry_id)
        word_len = len(current_entry)

        crossers = self.get_crossers(entry_id)

        possible_letters_map = {}
        for i, cw in enumerate(crossers):
            df_i = query.Query(db, **kwargs).match(str(cw)).limit(None).df()
            if len(df_i) == 0:
                return None
            idx_in_crosser = cw.cells.index(current_entry[i])
            possible_letters = {w[idx_in_crosser] for w in df_i["word"]}
            possible_letters_map[i] = possible_letters

        # TODO - to query!
        q = query.Query(default=False).length(word_len)
        for i, exclude_chars in exclude.items():
            q.exclude_letters(i, exclude_chars)

        for i, valid_letters in possible_letters_map.items():
            q.fix_letters(i, valid_letters)

        return q.df()

    def get_min_cell_list_spans(self) -> tuple[int, int]:
        """Computes the minimum word length in the horizontal/vertical directions

        Returns
        -------
        Tuple[int,int]
            Tuple of (h_max, v_max) representing the minimum word length in the horizontal/vertical directions

        """
        return self.h_starts["hlen"].min(), self.v_starts["vlen"].min()

    def get_max_cell_list_spans(self) -> tuple[int, int]:
        """Computes the maximum word length in the horizontal/vertical directions

        Returns
        -------
        Tuple[int,int]
            Tuple of (h_max, v_max) representing the maximum word length in the horizontal/vertical directions

        """
        return self.h_starts["hlen"].max(), self.v_starts["vlen"].max()

    def make_subgrid_from_words(self, word_ids: Iterable[str], **kwargs) -> "Grid":
        """Creates a subgrid from word IDs ("11A", "14D", etc.).

        Any set letters become locked int the subgrid, and any squares outside the ones
        in word_ids are set to black.

        Parameters
        ----------
        word_ids : Iterable[str]
            List of word IDs ("11A", "14D", etc.).
        kwargs
            Passed to the Grid constructor

        Returns
        -------
        Grid
            Newly created grid containing only the requested words (all others black)
        """

        cell_lists = [self.get_entry(w) for w in word_ids]

        # Get the size of the new grid based on the total span of the inputted cell lists
        xmin = min([w.x_range[0] for w in cell_lists])
        xmax = max([w.x_range[1] for w in cell_lists])
        ymin = min([w.y_range[0] for w in cell_lists])
        ymax = max([w.y_range[1] for w in cell_lists])

        xrange = (xmax - xmin) + 1
        yrange = (ymax - ymin) + 1

        # Collect list of grid locations (x,y) contained in the cell lists
        all_index_pairs = []
        for w in cell_lists:
            index_pairs = [(c.x, c.y) for c in w]
            all_index_pairs.extend(index_pairs)

        # Defaults for the new Grid
        kwargs.setdefault("symmetry", GridSymmetry.NONE)
        kwargs.setdefault("corpus", self.corpus)

        # Create new grid and set values/statuses from this grid
        subgrid = Grid(grid_size=(xrange, yrange), **kwargs)

        for xsub in range(xrange):
            for ysub in range(yrange):
                # 'sub' are coordinates in the new subgrid
                # 'orig' are coordinates in this grid
                xorig = xsub + xmin
                yorig = ysub + ymin
                cell_sub = subgrid[xsub, ysub]
                cell_orig = self[xorig, yorig]

                # Anything not in the index pairs list is black
                if (xorig, yorig) not in all_index_pairs:
                    cell_sub.status = CellStatus.BLACK
                    continue

                # Set value/status
                subgrid[xsub, ysub].value = cell_orig.value
                subgrid[xsub, ysub].status = (
                    CellStatus.LOCKED if cell_orig.status == CellStatus.SET else CellStatus.EMPTY
                )

        return subgrid

    def _is_h_start(self, i: int, j: int) -> bool:
        """Check if cell starts a horizontal word."""
        if self[i, j].status == CellStatus.BLACK:
            return False
        if j == 0:
            return True
        return self[i, j - 1].status == CellStatus.BLACK

    def _is_h_end(self, i: int, j: int) -> bool:
        """Check if cell ends a horizontal word."""
        if self[i, j].status == CellStatus.BLACK:
            return False
        if j == self.col_count - 1:
            return True
        return self[i, j + 1].status == CellStatus.BLACK

    def _is_v_start(self, i: int, j: int) -> bool:
        """Check if cell starts a vertical word."""
        if self[i, j].status == CellStatus.BLACK:
            return False
        if i == 0:
            return True
        return self[i - 1, j].status == CellStatus.BLACK

    def _is_v_end(self, i: int, j: int) -> bool:
        """Check if cell ends a vertical word."""
        if self[i, j].status == CellStatus.BLACK:
            return False
        if i == self.row_count - 1:
            return True
        return self[i + 1, j].status == CellStatus.BLACK

    def _traverse_cells(self, i: int, j: int, direction: GridDirection, terminate_on_empty: bool = False) -> list[Cell]:
        """Traverse cells in a given direction until boundary.

        Traverses from the starting cell in the specified direction,
        collecting cells until a word boundary or empty cell is reached.

        Parameters
        ----------
        i : int
            Starting row
        j : int
            Starting column
        which : GridDirection
            Direction to traverse (UP, DOWN, LEFT, RIGHT)
        terminate_on_empty : bool, optional
            Whether to stop at first empty cell (default: False)

        Returns
        -------
        list[Cell]
            List of cells including the starting cell.
            Returns empty list if starting cell is black.
        """
        cells = [self[i, j]]

        if cells[0].status == CellStatus.BLACK:
            return []

        # Define movement functions based on direction
        match GridDirection(direction):
            case GridDirection.UP:
                def should_stop(c):
                    return c.is_v_start or (terminate_on_empty and c.status == CellStatus.EMPTY)

                def next_cell(c):
                    return self[c.x - 1, c.y] if c.x > 0 else None

            case GridDirection.DOWN:

                def should_stop(c):
                    return c.is_v_end or (terminate_on_empty and c.status == CellStatus.EMPTY)

                def next_cell(c):
                    return self[c.x + 1, c.y] if c.x < self.row_count - 1 else None

            case GridDirection.LEFT:

                def should_stop(c):
                    return c.is_h_start or (terminate_on_empty and c.status == CellStatus.EMPTY)

                def next_cell(c):
                    return self[c.x, c.y - 1] if c.y > 0 else None

            case GridDirection.RIGHT:

                def should_stop(c):
                    return c.is_h_end or (terminate_on_empty and c.status == CellStatus.EMPTY)

                def next_cell(c):
                    return self[c.x, c.y + 1] if c.y < self.col_count - 1 else None

            case _:
                raise ValueError(f"Invalid direction: {direction}")

        # Traverse until boundary
        while not should_stop(cells[-1]):
            next_c = next_cell(cells[-1])
            if next_c is None:
                break
            cells.append(next_c)

        return cells

    def find_intersection(self, entry_id1: str, entry_id2: str) -> tuple[Cell, int, int] | None:
        """

        """
        word1 = self.get_entry(entry_id1)
        word2 = self.get_entry(entry_id2)


        # Create a lookup map for the first word's cells for efficient searching.
        # The key is the (x, y) coordinate tuple, and the value is the cell's index in word1.
        word1_map = {tuple(cell.matrix_index): i for i, cell in enumerate(word1.cells)}

        # Iterate through the second word to find a cell with a matching coordinate
        for i2, cell2 in enumerate(word2.cells):
            # Check if the cell's coordinate exists as a key in the first word's map
            if cell2.matrix_index in word1_map:
                # An intersection is found. Get the index from the first word.
                i1 = word1_map[cell2.matrix_index]

                # The intersecting cell is cell2 (which is the same as word1.cells[i1])
                return cell2, i1, i2

        # If the loop completes without finding a match, no intersection exists.
        return None


if __name__ == "__main__":
    lc = Corpus.from_lafarge(q=2)
    g = Grid((5, 5), lc)
    g.set_grid(1, 1, "B")
    g.set_grid(2, 2, "F")
    g[2, 2].status = CellStatus.LOCKED
    g[4, 4].status = CellStatus.BLACK

    x1, x2 = 0, 2
    c1, c2 = g.corner2center(x1, x2)

    g.to_console()

    g.print_lens(0)
    cl = g.cell_to_entry(4, 0, WordDirection.HORIZONTAL)

    # g.print_lens(1)

    # test_file = Path(project_root / "test_grid.xc")
    # # g.save(test_file)
    # g2 = Grid.load(test_file)
    # print()
    # g2.to_console()
