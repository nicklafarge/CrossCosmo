"""Crossword puzzle solver using trie-based backtracking algorithm."""

import logging
import time
from copy import deepcopy

import pygtrie

import crosscosmos as xc
from crosscosmos import constants
from crosscosmos.enums import LetterSequenceStatus, LetterStatus
from crosscosmos.grid import CellList, CellStatus, MoveDirection, WordDirection

logger = logging.getLogger(__name__)


def check_letter_sequence(
    cell: xc.grid.Cell, grid: xc.grid.Grid, trie_list: list[pygtrie.Trie], direction: WordDirection
) -> int:
    """Check if a letter sequence from a cell exists in the trie.

    Parameters
    ----------
    cell : xc.grid.Cell
        Starting cell for the word
    grid : xc.grid.Grid
        The crossword grid
    trie_list : list[pygtrie.Trie]
        List of tries indexed by word length
    direction : WordDirection
        Direction to check (HORIZONTAL or VERTICAL)

    Returns
    -------
    int
        Trie node status (HAS_VALUE, HAS_SUBTRIE, or doesn't exist)
    """
    cell_sequence = grid.full_word_from_cell(cell.x, cell.y, direction)

    # If they're all locked, call it a valid word
    if all(c.status == CellStatus.LOCKED for c in cell_sequence):
        return pygtrie.Trie.HAS_VALUE

    word_len = grid.word_len(cell.x, cell.y, direction)
    return trie_list[word_len].has_node(cell_sequence.to_first_placeholder())


def reset_cell_with_trie(grid: xc.grid.Grid, x: int, y: int, trie_list: list[pygtrie.Trie]) -> None:
    """Reset a cell and restore any removed words to the trie.

    Parameters
    ----------
    grid : xc.grid.Grid
        The crossword grid
    x : int
        Row coordinate
    y : int
        Column coordinate
    trie_list : list[pygtrie.Trie]
        List of tries indexed by word length
    """
    removed_words = grid[x, y].reset_cell()
    cell = grid[x, y]

    # Restore removed words to appropriate tries
    if removed_words:
        for word, direction in removed_words:
            match direction:
                case WordDirection.HORIZONTAL:
                    trie_list[cell.hlen][word] = True
                case WordDirection.VERTICAL:
                    trie_list[cell.vlen][word] = True


def move_back_horizontal(
    grid: xc.grid.Grid, x: int, y: int, trie_list: list[pygtrie.Trie]
) -> tuple[int, int, xc.GridStatus]:
    """Move backwards one cell horizontally in the grid.

    Resets the current cell and determines the previous cell position.
    If at the start of the grid, returns INVALID status.

    Parameters
    ----------
    grid : xc.grid.Grid
        The crossword grid
    x : int
        Current row coordinate
    y : int
        Current column coordinate
    trie_list : list[pygtrie.Trie]
        List of tries indexed by word length

    Returns
    -------
    tuple[int, int, xc.GridStatus]
        New x coordinate, new y coordinate, and grid status
    """
    # Check boundary conditions
    at_start = x == 0 and y == 0
    at_left_edge = y == 0

    # Reset current cell
    reset_cell_with_trie(grid, x, y, trie_list)

    if at_start:
        # No valid solution exists
        return x, y, xc.GridStatus.INVALID
    elif at_left_edge:
        # Move to end of previous row
        return x - 1, grid.col_count - 1, xc.GridStatus.INCOMPLETE
    else:
        # Move left one column
        return x, y - 1, xc.GridStatus.INCOMPLETE


def validate_grid_cell_list(grid_trie: pygtrie.Trie, cell_list: CellList, is_end_cell: bool) -> LetterSequenceStatus:
    """Validate a letter sequence against the trie.

    Checks if a letter sequence forms a valid word, valid subtrie, or is invalid.
    Trailing placeholders are ignored.

    A sequence with every element marked as "locked" is always considered valid, regardless of the trie.

    Parameters
    ----------
    grid_trie : pygtrie.Trie
        Trie containing valid words
    cell_list : CellList
        Cell list sequence to validate
    is_end_cell : bool
        Whether this is the final letter in a word

    Returns
    -------
    LetterSequenceStatus
        VALID_WORD, VALID_SUBTRIE, or INVALID
    """

    # If they're all locked, don't bother checking
    if all(c.status == CellStatus.LOCKED for c in cell_list):
        return LetterSequenceStatus.VALID_WORD

    to_first_placeholder = cell_list.to_first_placeholder()
    node_status = grid_trie.has_node(to_first_placeholder)

    has_placeholders = any(c in str(cell_list) for c in constants.PLACEHOLDERS)
    is_word_complete = not has_placeholders

    if node_status == pygtrie.Trie.HAS_VALUE:
        if is_end_cell:
            return LetterSequenceStatus.VALID_WORD
        if is_word_complete:
            return LetterSequenceStatus.VALID_SUBTRIE
    elif node_status == pygtrie.Trie.HAS_SUBTRIE:
        if not is_end_cell:
            return LetterSequenceStatus.VALID_SUBTRIE

    return LetterSequenceStatus.INVALID


def process_locked_cell(cell: xc.grid.Cell, grid: xc.grid.Grid, tries: list[pygtrie.Trie]) -> MoveDirection:
    """Process a locked cell and determine next move direction.

    Locked cells are pre-filled and cannot be changed. This function
    validates that the locked cell creates valid words/subtries.

    Parameters
    ----------
    cell : xc.grid.Cell
        The locked cell to process
    grid : xc.grid.Grid
        The crossword grid
    tries : list[pygtrie.Trie]
        List of tries indexed by word length

    Returns
    -------
    MoveDirection
        Direction to move next (FORWARD_HORIZONTAL or BACK_HORIZONTAL)
    """

    # Check if current sequences are valid
    h_valid = check_letter_sequence(cell, grid, tries, WordDirection.HORIZONTAL)
    v_valid = check_letter_sequence(cell, grid, tries, WordDirection.VERTICAL)

    # Move back if either direction is invalid
    if not h_valid or not v_valid:
        return MoveDirection.BACK_HORIZONTAL

    # Check end conditions
    if cell.is_h_end and h_valid == pygtrie.Trie.HAS_SUBTRIE:
        return MoveDirection.BACK_HORIZONTAL
    if cell.is_v_end and v_valid == pygtrie.Trie.HAS_SUBTRIE:
        return MoveDirection.BACK_VERTICAL

    return MoveDirection.FORWARD_HORIZONTAL


def find_valid_letter(
    cell: xc.grid.Cell, grid: xc.grid.Grid, tries: list[pygtrie.Trie]
) -> tuple[LetterStatus, MoveDirection]:
    """Find the next valid letter for a cell.

    Tries letters from the cell's queue until finding one that
    creates valid words/subtries in both directions.

    Parameters
    ----------
    cell : xc.grid.Cell
        Cell to fill with a letter
    grid : xc.grid.Grid
        The crossword grid
    tries : list[pygtrie.Trie]
        List of tries indexed by word length

    Returns
    -------
    tuple[LetterStatus, MoveDirection]
        Status of letter selection and next move direction
    """
    while grid[cell.x, cell.y].queue:
        # Try next letter
        grid[cell.x, cell.y].value = grid[cell.x, cell.y].queue.pop()
        grid[cell.x, cell.y].status = CellStatus.SET

        # Validate horizontal direction
        h_sequence = grid.full_word_from_cell(cell.x, cell.y, WordDirection.HORIZONTAL)
        h_status = validate_grid_cell_list(tries[cell.hlen], h_sequence, cell.is_h_end)

        # Validate vertical direction
        v_sequence = grid.full_word_from_cell(cell.x, cell.y, WordDirection.VERTICAL)
        v_status = validate_grid_cell_list(tries[cell.vlen], v_sequence, cell.is_v_end)

        # Accept letter if valid in both directions
        if h_status != LetterSequenceStatus.INVALID and v_status != LetterSequenceStatus.INVALID:
            # Remove completed words from tries to avoid duplicates
            if h_status == LetterSequenceStatus.VALID_WORD:
                tries[cell.hlen].pop(str(h_sequence))
                grid[cell.x, cell.y].remove_word(str(h_sequence), WordDirection.HORIZONTAL)

            if v_status == LetterSequenceStatus.VALID_WORD:
                tries[cell.vlen].pop(str(v_sequence))
                grid[cell.x, cell.y].remove_word(str(v_sequence), WordDirection.VERTICAL)

            return LetterStatus.VALID, MoveDirection.FORWARD_HORIZONTAL

    # No valid letters found
    return LetterStatus.INVALID, MoveDirection.BACK_HORIZONTAL


def move_forward(grid: xc.grid.Grid, x: int, y: int) -> tuple[int, int, xc.GridStatus]:
    """Move forward one cell in the grid.

    Moves left-to-right, top-to-bottom through the grid.

    Parameters
    ----------
    grid : xc.grid.Grid
        The crossword grid
    x : int
        Current row coordinate
    y : int
        Current column coordinate

    Returns
    -------
    tuple[int, int, xc.GridStatus]
        New x coordinate, new y coordinate, and grid status
    """
    # Check if at end of grid
    if x == grid.row_count - 1 and y == grid.col_count - 1:
        return x, y, xc.GridStatus.COMPLETE

    # Move to next column
    if y < grid.col_count - 1:
        return x, y + 1, xc.GridStatus.INCOMPLETE

    # Move to next row
    return x + 1, 0, xc.GridStatus.INCOMPLETE


def move_backward_vertical(
    grid: xc.grid.Grid, x: int, y: int, tries: list[pygtrie.Trie]
) -> tuple[int, int, xc.GridStatus]:
    """Move backward vertically, resetting affected cells.

    Resets all cells to the left of current position and
    all cells to the right on the row above.

    Parameters
    ----------
    grid : xc.grid.Grid
        The crossword grid
    x : int
        Current row coordinate
    y : int
        Current column coordinate
    tries : list[pygtrie.Trie]
        List of tries indexed by word length

    Returns
    -------
    tuple[int, int, xc.GridStatus]
        New x coordinate, new y coordinate, and grid status
    """
    # Reset cells to the left
    for col in range(y):
        reset_cell_with_trie(grid, x, col, tries)

    # Reset cells to the right on row above
    if x > 0:
        for col in range(y, grid.col_count):
            reset_cell_with_trie(grid, x - 1, col, tries)
        return x - 1, y, xc.GridStatus.INCOMPLETE

    return x, y, xc.GridStatus.INVALID


def solve(grid: xc.grid.Grid, max_time: float = 30) -> None:
    """Solve a crossword puzzle using backtracking with tries.

    Uses a depth-first search approach, trying letters from a corpus
    and backtracking when invalid configurations are found.

    Parameters
    ----------
    grid : xc.grid.Grid
        The crossword grid to solve
    max_time : float, optional
        Maximum solving time in seconds (default: 30)
    """

    tries = deepcopy(grid.tries)
    grid_status = xc.GridStatus.INCOMPLETE
    start_time = time.time()

    # Start at top-left corner
    x, y = 0, 0
    n_iters = 0

    while grid_status == xc.GridStatus.INCOMPLETE:
        n_iters += 1

        # Check time limit periodically
        if n_iters % 500 == 0:
            if time.time() - start_time > max_time:
                logger.warning("Max solve time exceeded")
                return
            grid.print()
            print()

        # print(f"{x=},{y=}")
        cell = grid[x, y]

        # Handle special cell types
        if cell.status == CellStatus.BLACK:
            x, y, grid_status = move_forward(grid, x, y)
            continue

        if cell.status == CellStatus.LOCKED:
            move_dir = process_locked_cell(cell, grid, tries)
        else:
            # Find valid letter for current cell
            letter_status, move_dir = find_valid_letter(cell, grid, tries)

        # Execute move based on direction
        match move_dir:
            case MoveDirection.FORWARD_HORIZONTAL:
                x, y, grid_status = move_forward(grid, x, y)

            case MoveDirection.BACK_HORIZONTAL:
                # Move back to previous non-locked/non-black cell
                while True:
                    x, y, grid_status = move_back_horizontal(grid, x, y, tries)
                    if grid_status == xc.GridStatus.INVALID:
                        break
                    if grid[x, y].status not in (CellStatus.BLACK, CellStatus.LOCKED):
                        break

            case MoveDirection.BACK_VERTICAL:
                x, y, grid_status = move_backward_vertical(grid, x, y, tries)

    # Print final result
    match grid_status:
        case xc.GridStatus.COMPLETE:
            logger.info("Grid complete!")
        case xc.GridStatus.INVALID:
            logger.error("No valid solution found for grid")
    grid.print()


if __name__ == "__main__":
    # test_corpus = xc.corpus.Corpus.from_test()
    # test_corpus = xc.corpus.Corpus.from_diehl()
    grid_size = (9, 8)

    test_corpus = xc.corpus.Corpus.from_lafarge(max_length=8, q=1)

    test_grid = xc.grid.Grid(grid_size, test_corpus, shuffle=False)
    test_grid.build_tries()

    # test_grid.set_word("MLADY", 0, 0, 0, True)
    # test_grid.set_word("LAFC", 0, 0, 0, True)
    # test_grid.set_word("DNER", 1, 0, 0, True)
    # test_grid.set_word("RELO", 2, 0, 0, True)
    # test_grid.set_word("ST", 3, 0, 0, True)
    test_grid.set_word("PILLOW", 0, 0, 0, True)
    test_grid.set_word("TREE", 3, 1, 0, True)
    # test_grid.set_word([None, None, None], 4, 0, 0)
    # test_grid.set_word([None, None, None], 5, 0, 0)
    # test_grid.set_word([None, None, None], 6, 0, 0)
    print(test_grid)
    # test_grid.update_length_and_head_data()

    test_grid.reset_for_solving()
    solve(test_grid)

    from crosscosmos.gui import grid_gui
    grid_gui.run_default(test_grid)
