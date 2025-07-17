# Standard library
import copy

# Third-pary
import numpy as np

# Local
import crosscosmos as xc



test_corpus = xc.corpus.Corpus.from_test()
grid = xc.grid.Grid((3, 5), test_corpus, shuffle=True)
grid.set_word("CLASP", 0, 0, xc.WordDirection.HORIZONTAL, lock=True)
grid.print()

# List of cells to go through
x = 0
y = 0
word_direction = xc.WordDirection.VERTICAL
opposite_dir = xc.WordDirection.flip(word_direction)
cell_list = grid.full_word_from_cell(x=x,
                                     y=y,
                                     direction=word_direction,
                                     terminate_on_empty=False)

# Copy for later
original_grid = copy.deepcopy(grid)

# Total possible words for candidate cell list
possible_words = xc.query.match(test_corpus, str(cell_list))

# That counts the number of possible entries

n_valid = np.zeros(len(possible_words), dtype=int)

for i, w in enumerate(possible_words):
    grid.set_word(w.word, x, y, word_direction)
    grid_status, n_possible = grid.count_possible(cell_list, query_level=2)
    n_valid[i] = n_possible

options = sorted([(n, w) for n, w in zip(possible_words, n_valid)], key=lambda v: v[0])

# Reset grid
grid = original_grid
