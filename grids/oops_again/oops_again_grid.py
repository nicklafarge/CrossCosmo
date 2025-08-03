from pathlib import Path

import crosscosmos as xc
from crosscosmos.wordlists import LaFargeWord


grid_path = Path(__file__).parent / "mighty_matiss.json"
# grid_path = Path(__file__).parent / "oops_again2.json"
xc_grid = xc.grid.Grid.load(grid_path)

xc.grid_gui.run_default(xc_grid)