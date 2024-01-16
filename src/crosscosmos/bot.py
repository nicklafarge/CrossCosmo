# Third-party
import logging
import pygtrie

# CrossCosmos
import crosscosmos as xc
from crosscosmos.grid import CellStatus

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    lc = xc.corpus.Corpus.from_test()
    lc4 = lc.to_n_letter_corpus(4)
    lc4.build_trie()
    trie = lc4.trie

    grid = xc.grid.Grid((4, 4), lc4)
    grid.print()
    grid.print_boundaries()

    # for i in range(grid.row_count):
    #     for j in range(grid.col_count):
    i = 0
    j = 0
    grid_full = False
    h_word_counter = 0
    while not grid_full:
        c = grid[i, j]

        # Get the next value that exists
        move_back = False
        val_is_valid = False

        # Continue on if this square is black
        if c.status == CellStatus.BLACK:
            val_is_valid = True

        # Continue on if this is locked, move back if the subtrie or word isn't valid
        if c.status == CellStatus.LOCKED:
            val_is_valid = True

            word_to_xy = grid.get_h_word_up_to(c.x, c.y)
            t_has_node = trie.has_node(word_to_xy)
            if not t_has_node:
                move_back = True
            elif c.is_h_end and t_has_node == pygtrie.Trie.HAS_SUBTRIE:
                move_back = True

        # Look for a valid letter
        while not val_is_valid:

            if len(grid[i, j].queue) == 0:
                move_back = True
                break

            # Update actual value for c within grid
            grid[i, j].value = grid[i, j].queue.pop()
            grid[i, j].status = CellStatus.SET

            h_word_to_xy = grid.get_h_word_up_to(c.x, c.y)
            v_word_to_xy = grid.get_v_word_up_to(c.x, c.y)

            trie_has_h_node = trie.has_node(h_word_to_xy)
            trie_has_v_node = trie.has_node(v_word_to_xy)

            # Must be valid in both horizontal and vertical directions
            if c.is_h_end and trie_has_h_node == pygtrie.Trie.HAS_VALUE:
                val_is_valid = True
            elif not c.is_h_end and trie_has_h_node == pygtrie.Trie.HAS_SUBTRIE:
                val_is_valid = True

            if c.is_v_end and trie_has_v_node == pygtrie.Trie.HAS_VALUE:
                val_is_valid = True
            elif not c.is_v_end and trie_has_v_node == pygtrie.Trie.HAS_SUBTRIE:
                val_is_valid = True

        # Move back one index if instructed
        grid.print()
        if move_back:
            c.reset_cell()
            if j > 0:
                j -= 1
            elif j == 0 and i > 0:
                j = grid.col_count - 1
                i -= 1
            else:
                raise EOFError("No Solutions Found for Grid")
        else:
            if j < grid.col_count - 1:
                j += 1
            elif j == grid.col_count - 1 and i < grid.row_count - 1:
                j = 0
                i += 1
            else:
                grid_full = True  # COMPLETE!

        # Move right until we can't
        # while hj < grid.col_count and c.status != CellStatus.BLACK:
        #
        #     Go to the next cell
        # j += 1
