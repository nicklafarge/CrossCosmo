""" """

import crosscosmos as xc
from crosscosmos import bot

grid_size = (9, 8)


test_corpus = xc.corpus.Corpus.from_lafarge(max_length=8, q=1)
test_grid = xc.grid.Grid(grid_size, test_corpus, shuffle=True)
test_grid.build_tries()

test_grid.set_black(0, 0, 4, 0)
test_grid.set_black(1, 0, 4, 0)
test_grid.set_black(4, 6, 2, 0)
test_grid.set_black(5, 0, 3, 0)
test_grid.set_black(6, 0, 4, 0)
test_grid.set_black(7, 0, 4, 0)
test_grid.set_black(8, 0, 4, 0)
test_grid.set_black(8, 5, 3, 0)


test_grid.set_word("USTMEBRO", 2, 0, 0, True)
test_grid.set_word("KSSAFE", 4, 0, 0, True)
test_grid.set_word("ORDS", 7, 4, 0, True)
test_grid.set_word("OPENFLOOR", 0, 4, 1, True)
print(test_grid)

test_grid.reset_for_solving()
bot.solve(test_grid, max_time=60*10)