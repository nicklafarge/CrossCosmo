"""
Defines a crossword Grid class, interfacing between the data and gui laters

"""

from dataclasses import dataclass
import copy
import logging
import random
from pathlib import Path

from crosscosmos import constants, io_utils
from crosscosmos.enums import CellStatus, WordDirection

logger = logging.getLogger(__name__)


@dataclass
class Cell:
    """Individual cell in a crossword grid.

    Contains the state, value, and coordinates of a single grid position.

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

    """

    def __init__(
        self,
        x: int,
        y: int,
        status: CellStatus = CellStatus.EMPTY,
        value: str = "",
        gui_coordinates: tuple[float, float] | None = None,
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

    def to_dict(self) -> dict:
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
        cell.matrix_index = json_cell["matrix_index"]
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
        io_utils.save_json_dict(filename, self.to_dict())
