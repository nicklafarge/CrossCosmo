# Standard
from enum import Enum

# Third-party
import logging
import pygtrie

# CrossCosmos
import crosscosmos as xc
from crosscosmos.grid import CellStatus

logger = logging.getLogger(__name__)


class GridStatus(Enum):
    COMPLETE = 1
    INCOMPLETE = 2
    INVALID = 3


class MoveDirection(Enum):
    FORWARD = 1
    BACK = 2


class LetterStatus(Enum):
    VALID = 1
    INVALID = 2


class LetterSequenceStatus(Enum):
    INVALID = 1
    VALID_SUBTRIE = 2
    VALID_WORD = 3


def get_previous_cell_index(i: int, j: int):
    pass


def validate_grid_letter_sequence(grid_trie: pygtrie, letter_sequence: str, is_end: bool) -> LetterSequenceStatus:
    node_in_trie = grid_trie.has_node(letter_sequence)
    if is_end and node_in_trie == pygtrie.Trie.HAS_VALUE:
        return LetterSequenceStatus.VALID_WORD
    elif not is_end and node_in_trie == pygtrie.Trie.HAS_SUBTRIE:
        return LetterSequenceStatus.VALID_SUBTRIE
    else:
        return LetterSequenceStatus.INVALID


if __name__ == '__main__':
    lc = xc.corpus.Corpus.from_test()
    lc4 = lc.to_n_letter_corpus(4)
    lc4.build_trie()
    trie = lc4.trie

    grid = xc.grid.Grid((4, 4), lc4)
    grid.print()
    grid.print_boundaries()
    grid_status = GridStatus.INCOMPLETE

    # Start in top left (0, 0)
    i = 0
    j = 0

    # Get the next value that exists
    while grid_status == grid_status.INCOMPLETE:
        c = grid[i, j]

        # Initialize variables
        move_dir = MoveDirection.FORWARD
        letter_status = LetterStatus.INVALID

        # Continue on if this square is black
        if c.status == CellStatus.BLACK:
            letter_status = LetterStatus.VALID

        # When a locked square is encountered, do the following:
        #    - Locked squared are always treated as valid
        #    - Move back if adding the locked square's value creates an invalid subtrie
        #    - Move back if the locked square is at a barrier and a word isn't formed
        if c.status == CellStatus.LOCKED:

            # A locked square is automatically considered "Valid"
            letter_status = LetterStatus.VALID

            # Get the cross word up to this point
            word_to_xy = grid.get_h_word_up_to(c.x, c.y)

            # See if the word up to now is valid. If not, move back
            t_has_node = trie.has_node(word_to_xy)
            if not t_has_node:
                move_dir = MoveDirection.BACK

            # If we've reached a horizontal barrier and don't have a word, then move back
            if c.is_h_end and t_has_node == pygtrie.Trie.HAS_SUBTRIE:
                move_dir = MoveDirection.BACK

        # Choose the next letter by proceeding through the grid entry's letter list and selecting the
        # first letter than yields a valid subtrie
        while letter_status != LetterStatus.VALID:

            # If there are no more letters, then no word exists, and we need to move back
            if len(grid[i, j].queue) == 0:
                move_dir = MoveDirection.BACK
                break

            # Set the value in the grid with the next letter in the queue
            grid[i, j].value = grid[i, j].queue.pop()
            grid[i, j].status = CellStatus.SET

            # Check if the horizontal letter sequence is valid
            h_word_to_xy = grid.get_h_word_up_to(c.x, c.y)
            horizontal_word_status = validate_grid_letter_sequence(trie, h_word_to_xy, c.is_h_end)
            horizontal_letter_accepted = horizontal_word_status != LetterSequenceStatus.INVALID

            # Check if the vertical letter sequence is valid
            v_word_to_xy = grid.get_v_word_up_to(c.x, c.y)
            vertical_word_status = validate_grid_letter_sequence(trie, v_word_to_xy, c.is_v_end)
            vertical_letter_accepted = vertical_word_status != LetterSequenceStatus.INVALID

            # The selected letter is only accepted if it is valid in both vertical and horizontal directions
            if horizontal_letter_accepted and vertical_letter_accepted:
                letter_status = letter_status.VALID

                # If horizontal word is complete, remove it to avoid duplication
                if horizontal_word_status == LetterSequenceStatus.VALID_WORD:
                    trie.pop(h_word_to_xy)
                    grid[i, j].removed_words.append(h_word_to_xy)

                # If vertical word is complete, remove it to avoid duplication
                if vertical_word_status == LetterSequenceStatus.VALID_WORD:
                    trie.pop(v_word_to_xy)
                    grid[i, j].removed_words.append(v_word_to_xy)

        # For debugging
        grid.print()

        # Save for readability
        on_left_column = j == 0
        on_right_column = j == (grid.col_count - 1)
        on_top_row = i == 0
        on_bottom_row = i == (grid.row_count - 1)

        # If an invalid configuration is encountered, move back to the previous cell and reset the current one

        match move_dir:
            case MoveDirection.FORWARD:
                if on_bottom_row and on_right_column:  # COMPLETE!
                    grid_status = GridStatus.COMPLETE
                if j < grid.col_count - 1:
                    j += 1
                elif j == grid.col_count - 1 and i < grid.row_count - 1:
                    j = 0
                    i += 1

            case MoveDirection.BACK:
                # Reset the cell's status
                removed_words = grid[i, j].reset_cell()

                # If the cell had previously removed a word from the trie put it back in
                if removed_words:
                    for w in removed_words:
                        trie[w] = True

                if on_left_column and on_top_row:  # We aren't square one an out of options!
                    grid_status = GridStatus.INVALID
                elif on_left_column:  # Move one row up to the right-most column
                    j = grid.col_count - 1
                    i -= 1
                else:  # Move one square to the left
                    j -= 1

    match grid_status:
        case GridStatus.COMPLETE:
            print("Grid complete!")
        case GridStatus.INVALID:
            print("No valid solution found for grid")
    grid.print()
