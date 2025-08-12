""" """
from pathlib import Path
import logging

import crosscosmos as xc

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

grid_path = Path("oops_again1.json").resolve()
grid = xc.grid.Grid.load(grid_path)

print("\nLoading word database...")
min_score = 20
word_df = xc.Query(db=xc.LaFargeWord, default=False, limit=None).min_score(min_score).df()
print(f"Loaded {len(word_df)} words with score >= {min_score}")

# Initialize solver
print("Running Solver!")
solver = xc.GridPruningSolver(grid=grid, word_df=word_df)
stats = solver.solve()
solver.print_possibilities_grid()


cells = sorted([c for c in grid.grid.flatten() if c.status == xc.CellStatus.EMPTY], key= lambda c: len(c.possible_letters))


words6a = solver.get_valid_entries(grid["6A"])
words25d = solver.get_valid_entries(grid["25D"])
words116A = solver.get_valid_entries(grid["116A"])