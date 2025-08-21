""" """

import logging

import crosscosmos as xc

logger = logging.getLogger(__name__)

df = xc.Query(default=False, q=2, limit=200000).max_length(12).df()

grid = xc.Grid((12, 12), auto_symmetry=True)

bricks = [
    (0, 5),
    (1, 5),
    (2, 5),
    (3, 4),
    (4, 3),
    (6, 5),
    (7, 0),
    (7, 1),
    (7, 2),
    (8, 3),
]
for b in bricks:
    grid[b[0], b[1]] = None



# grid.set_word("SIMPSON", 5, 0, 0)

run_solver = False
grid.set_entry("20D", "FRANKLIN")
grid.set_entry("1D", "OCCLUDE")
grid.set_entry("2D", "SENATOR")
grid.set_entry("1A", "OSAKA")
grid.set_entry("4D", "KATY")
gui = xc.run_gui(grid, df, run_solver=run_solver)