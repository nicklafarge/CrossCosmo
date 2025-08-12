""" """

import logging

import crosscosmos as xc

logger = logging.getLogger(__name__)

df = xc.Query(default=False, q=4, limit=None).max_length(6).df()

grid = xc.Grid((5, 5))
grid[0, 4] = None
grid[1, 4] = None
grid[4, 0] = None
grid[4, 1] = None

grid[0,0] = "R"
grid[1,0] = "O"
grid[2,0] = "S"
grid[3,0] = "E"

grid[0,1] = "O"
grid[0,2] = "S"
grid[0,3] = "S"
# grid[3,0] = "L"
gui = xc.run_gui(grid, df)