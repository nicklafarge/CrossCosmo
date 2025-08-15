from pathlib import Path

import crosscosmos as xc
from crosscosmos.wordlists import LaFargeWord
from crosscosmos.gui.new_grid import run_gui

import logging
logging.getLogger().setLevel(logging.INFO)


# grid_path = Path(__file__).parent / "mighty_matiss.json"
grid_path = Path(__file__).parent / "oops_again1.json"
xc_grid = xc.grid.Grid.load(grid_path)

print("\nLoading word database...")
min_score = 30
word_df = xc.Query(db=xc.LaFargeWord, default=False, limit=None).min_score(min_score).df()
print(f"Loaded {len(word_df)} words with score >= {min_score}")

gui = run_gui(grid=xc_grid, df=word_df)