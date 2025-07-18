from pathlib import Path
from crosscosmos.gui import grid_gui
import crosscosmos as xc

grid_path = Path(__file__).parent / 'space_missions.json'
xc_grid = xc.grid.Grid.load(grid_path)
# xc_grid.corpus = xc.corpus.Corpus.from_lafarge()

grid_gui.run_default(xc_grid)