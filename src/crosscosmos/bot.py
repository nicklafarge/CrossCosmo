# Standard
from enum import Enum
from typing import List

# Third-party
import logging
import pygtrie

# CrossCosmos
import crosscosmos as xc
from crosscosmos.grid import CellStatus, WordDirection, MoveDirection

logger = logging.getLogger(__name__)


class GridStatus(Enum):
    COMPLETE = 1
    INCOMPLETE = 2
    INVALID = 3


class LetterStatus(Enum):
    VALID = 1
    INVALID = 2


class LetterSequenceStatus(Enum):
    INVALID = 1
    VALID_SUBTRIE = 2
    VALID_WORD = 3


def check_letter_sequence(cell, the_grid, trie_list, direction: WordDirection):
    cell_sequence = the_grid.full_word_from_cell(cell.x, cell.y, direction)
    letter_sequence = ''.join([c.value for c in cell_sequence if c.value])
    word_len = the_grid.word_len(cell.x, cell.y, direction)
    return trie_list[word_len].has_node(letter_sequence)


def reset_cell_with_trie(the_grid, x: int, y: int, trie_list: List[pygtrie]):
    # Reset the cell's status
    removed_words = the_grid[x, y].reset_cell()
    c = the_grid[x, y]

    # If the cell had previously removed a word from the trie put it back in
    if removed_words:
        for rem_word, rem_dir in removed_words:
            match rem_dir:
                case WordDirection.HORIZONTAL:
                    trie_list[c.hlen][rem_word] = True
                case WordDirection.VERTICAL:
                    trie_list[c.vlen][rem_word] = True


def move_back_horizontal(grid, x: int, y: int, trie_list):
    # Save for readability
    on_left_column = y == 0
    on_right_column = y == (grid.col_count - 1)
    on_top_row = x == 0
    on_bottom_row = x == (grid.row_count - 1)

    reset_cell_with_trie(grid, x, y, trie_list)
    new_x = x
    new_y = y
    status = GridStatus.INCOMPLETE
    if on_left_column and on_top_row:  # We are at square one and out of options!
        status = GridStatus.INVALID
    elif on_left_column:  # Move one row up to the right-most column
        new_y = grid.col_count - 1
        new_x -= 1
    else:  # Move one square to the left
        new_y -= 1

    return new_x, new_y, status


def validate_grid_letter_sequence(grid_trie: pygtrie, letter_sequence: str, is_end: bool) -> LetterSequenceStatus:
    node_in_trie = grid_trie.has_node(letter_sequence)
    if is_end and node_in_trie == pygtrie.Trie.HAS_VALUE:
        return LetterSequenceStatus.VALID_WORD
    elif not is_end and node_in_trie == pygtrie.Trie.HAS_SUBTRIE:
        return LetterSequenceStatus.VALID_SUBTRIE
    else:
        return LetterSequenceStatus.INVALID


def solve(grid: xc.grid.Grid):
    # Build tries
    # tries = grid.corpus.to_n_tries(8, padded=True)
    tries = grid.tries

    grid_status = GridStatus.INCOMPLETE
    # Start in top left (0, 0)
    i = 0
    j = 0

    # Track iterations
    n_iters = 0

    # Get the next value that exists
    while grid_status == grid_status.INCOMPLETE:

        n_iters += 1
        if n_iters % 1000 == 0:
            grid.print()
            print()

        # Get the current grid value
        c = grid[i, j]

        # Initialize variables
        move_dir = MoveDirection.FORWARD_HORIZONTAL
        letter_status = LetterStatus.INVALID

        # Continue on if this square is black (automatically considered valid)
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
            trie_has_h_word = check_letter_sequence(c, grid, tries, WordDirection.HORIZONTAL)
            trie_has_v_word = check_letter_sequence(c, grid, tries, WordDirection.VERTICAL)

            # See if the word up to now is valid. If not, move back
            if not trie_has_h_word or not trie_has_v_word:
                move_dir = MoveDirection.BACK_HORIZONTAL

            # If either is true, move back one square to the left:
            #     1) the horizontal word up to now is invalid
            #     2) we've reached a horizontal barrier and don't have a valid word
            if c.is_h_end and trie_has_h_word == pygtrie.Trie.HAS_SUBTRIE:
                move_dir = MoveDirection.BACK_HORIZONTAL

            # If either is true, move back one square up:
            #     1) the vertical word up to now is invalid
            #     2) we've reached a vertical barrier and don't have a valid word
            if c.is_v_end and trie_has_v_word == pygtrie.Trie.HAS_SUBTRIE:
                move_dir = MoveDirection.BACK_VERTICAL

        # TODO: for longer words, maybe skip the letter looping but instead just look for 8(or whatever) letter 
        #  words starting with what is currently in the grid

        # TODO: need for some longer DB-style checking
        #   queryL length(word)==7 AND SUBSTRING(word,3,1)=='E' AND SUBSTRING(word,8,1)=='A'
        #   if no results, then return. If 1 result, then fill.

        # Choose the next letter by proceeding through the grid entry's letter list and selecting the
        # first letter than yields a valid subtrie
        while letter_status != LetterStatus.VALID:

            # If there are no more letters, then no word exists, and we need to move back
            if len(grid[i, j].queue) == 0:
                move_dir = MoveDirection.BACK_HORIZONTAL
                break

            # Set the value in the grid with the next letter in the queue
            grid[i, j].value = grid[i, j].queue.pop()
            grid[i, j].status = CellStatus.SET

            # Check if the horizontal letter sequence is valid

            h_cell_sequence = grid.full_word_from_cell(c.x, c.y, WordDirection.HORIZONTAL)
            h_word_fragment = ''.join([c.value for c in h_cell_sequence if c.value])
            horizontal_word_status = validate_grid_letter_sequence(tries[c.hlen], h_word_fragment, c.is_h_end)
            horizontal_letter_accepted = horizontal_word_status != LetterSequenceStatus.INVALID

            # Check if the vertical letter sequence is valid
            v_cell_sequence = grid.full_word_from_cell(c.x, c.y, WordDirection.VERTICAL)
            v_word_fragment = ''.join([c.value for c in v_cell_sequence if c.value])
            vertical_word_status = validate_grid_letter_sequence(tries[c.vlen], v_word_fragment, c.is_v_end)
            vertical_letter_accepted = vertical_word_status != LetterSequenceStatus.INVALID

            # The selected letter is only accepted if it is valid in both vertical and horizontal directions
            if horizontal_letter_accepted and vertical_letter_accepted:
                letter_status = letter_status.VALID

                # If horizontal word is complete, remove it to avoid duplication
                if horizontal_word_status == LetterSequenceStatus.VALID_WORD:
                    tries[c.hlen].pop(h_word_fragment)
                    grid[i, j].remove_word(h_word_fragment, WordDirection.HORIZONTAL)

                # If vertical word is complete, remove it to avoid duplication
                if vertical_word_status == LetterSequenceStatus.VALID_WORD:
                    tries[c.vlen].pop(v_word_fragment)
                    grid[i, j].remove_word(v_word_fragment, WordDirection.VERTICAL)

        # For debugging
        # grid.print()

        # Save for readability
        on_left_column = j == 0
        on_right_column = j == (grid.col_count - 1)
        on_top_row = i == 0
        on_bottom_row = i == (grid.row_count - 1)

        # If an invalid configuration is encountered, move back to the previous cell and reset the current one

        match move_dir:
            case MoveDirection.FORWARD_HORIZONTAL:
                if on_bottom_row and on_right_column:  # COMPLETE!
                    grid_status = GridStatus.COMPLETE
                if j < grid.col_count - 1:
                    j += 1
                elif j == grid.col_count - 1 and i < grid.row_count - 1:
                    j = 0
                    i += 1

            case MoveDirection.BACK_HORIZONTAL:
                # Move back until a non-locked cell is encountered
                continue_moving = True
                while continue_moving:
                    i, j, grid_status = move_back_horizontal(grid, i, j, tries)
                    if grid_status == GridStatus.INVALID:
                        continue_moving = False
                    elif grid[i, j].status == CellStatus.BLACK or grid[i, j].status == CellStatus.LOCKED:
                        continue_moving = True
                    else:
                        continue_moving = False

            case MoveDirection.BACK_VERTICAL:

                for left_of_cell in range(j):
                    reset_cell_with_trie(grid, i, left_of_cell, tries)
                for right_of_above in range(grid.col_count - j):
                    reset_cell_with_trie(grid, i - 1, right_of_above, tries)

                if on_top_row:  # Undefined behavior
                    grid_status = GridStatus.INVALID
                else:  # Move one square up the left
                    i -= 1
    match grid_status:
        case GridStatus.COMPLETE:
            print("Grid complete!")
        case GridStatus.INVALID:
            print("No valid solution found for grid")
    grid.print()


if __name__ == '__main__':
    # corpus = xc.corpus.Corpus.from_test()
    # corpus = xc.corpus.Corpus.from_diehl()
    test_corpus = xc.corpus.Corpus.from_lafarge()
    # lc4 = lc.to_n_letter_corpus(4)
    # lc5 = lc.to_subcorpus(4, 5)
    # lc6 = lc.to_subcorpus(4, 6)
    # tries = corpus.to_n_tries(8, padded=True)
    # lc4.build_trie()
    # trie = lc4.trie
    # lc.build_trie()
    # trie = lc.trie

    # corpus = lc
    # corpus.build_trie()
    # trie = corpus.trie

    test_grid = xc.grid.Grid((3, 5), test_corpus, shuffle=True)
    # grid.set_grid(0, 5, None)
    # grid.set_grid(0, 4, None)
    # grid.set_grid(3, 0, None)
    # grid.set_grid(3, 1, None)

    # grid.lock_section("LIENE", 2, 0, WordDirection.HORIZONTAL)
    # grid.lock_section("SAD", 0, 0, WordDirection.VERTICAL)
    # grid.lock_section("PRO", 0, 1, WordDirection.VERTICAL)

    # grid[0, 0].status = CellStatus.BLACK
    # grid.lock_section("ACER", 0, 0, direction=WordDirection.HORIZONTAL)
    # grid.lock_section("", 0, 0, direction=WordDirection.VERTICAL)
    # grid.lock_section("PAT", 0, 1, direction=WordDirection.HORIZONTAL)
    # grid.lock_section("TOOTHY", 0, 3, direction=WordDirection.VERTICAL)
    test_grid.update_grid_data()
    test_grid.print()
    print()
    test_grid.print_lens(direction=WordDirection.HORIZONTAL)
    print()
    test_grid.print_lens(direction=WordDirection.VERTICAL)
    print()
    test_grid.print_boundaries()
    solve(test_grid)