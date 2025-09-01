from pathlib import Path

import crosscosmos as xc
from crosscosmos.archive import grid_gui

grid_path = Path(__file__).parent / "flw2.json"
xc_grid = xc.grid.Grid.load(grid_path)
# xc_grid.corpus = xc.corpus.Corpus.from_lafarge()


df = xc.Query(default=False, q=2, limit=None).max_length(21).df()
gui = grid_gui.run_default(xc_grid, df)
